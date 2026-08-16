"""Tests du moteur de facturation et d'optimisation."""

import pytest

from moteur import facturation, optimisation, tarifs


def test_repartition_tranches_dpp():
    # DPP : tranche 1 jusqu'à 150 kWh, tranche 2 jusqu'à 250 kWh
    assert facturation.repartir_tranches(100, (150, 250)) == (100, 0, 0)
    assert facturation.repartir_tranches(200, (150, 250)) == (150, 50, 0)
    assert facturation.repartir_tranches(400, (150, 250)) == (150, 100, 150)


def test_facture_bt_dpp_premiere_tranche():
    f = facturation.facture_bt("DPP", 100, redevance=0.0)
    montant_ht = 100 * 90.47
    assert f.montant_ht == pytest.approx(montant_ht)
    assert f.tco == pytest.approx(montant_ht * 0.025)
    # Usage domestique sans troisième tranche : TVA nulle hors redevance
    assert f.tva == pytest.approx(0.0)
    assert f.total_ttc == pytest.approx(montant_ht * 1.025)


def test_facture_bt_professionnel_tva_sur_tout():
    f = facturation.facture_bt("PPP", 100, redevance=0.0)
    montant_ht = 50 * 128.85 + 50 * 135.68
    base_tva = montant_ht * 1.025
    assert f.tva == pytest.approx(base_tva * 0.18)
    assert f.total_ttc == pytest.approx(montant_ht + montant_ht * 0.025 + base_tva * 0.18)


def test_woyofal_troisieme_tranche_plafonnee():
    postpaye = facturation.facture_bt("DPP", 400)
    woyofal = facturation.facture_bt("DPP", 400, woyofal=True)
    assert woyofal.montant_ht < postpaye.montant_ht
    ecart_ht = 150 * (112.65 - 101.64)
    assert postpaye.montant_ht - woyofal.montant_ht == pytest.approx(ecart_ht)


def test_facture_speciale_prime_fixe_et_energie():
    f = facturation.facture_speciale("MT-TG", 1000, 200, 100,
                                     redevance=0.0)
    attendu = 1000 * 85.29 + 200 * 136.46 + 100 * 3861.89
    assert f.montant_ht == pytest.approx(attendu)
    assert f.tco == 0.0            # pas de taxe communale en moyenne tension
    assert f.tva == pytest.approx(attendu * 0.18)


def test_tco_grande_puissance_bt():
    f = facturation.facture_speciale("PGP", 1000, 200, 50, redevance=0.0)
    assert f.tco == pytest.approx(f.montant_ht * 0.025)


def test_penalite_depassement():
    sans = facturation.facture_speciale("MT-TG", 0, 0, 100, redevance=0.0)
    avec = facturation.facture_speciale("MT-TG", 0, 0, 100, pmax_kw=120,
                                        redevance=0.0)
    penalite = 20 * 3861.89 * tarifs.COEF_DEPASSEMENT_PS
    assert avec.montant_ht - sans.montant_ht == pytest.approx(penalite)


def test_cos_phi_et_application():
    # tan phi = 0.75 -> cos phi = 0.8 : aucune application
    assert facturation.cos_phi(4000, 3000) == pytest.approx(0.8)
    assert tarifs.taux_application(0.80) == 0.0
    assert tarifs.taux_application(0.78) == 0.05
    assert tarifs.taux_application(0.39) == 0.80
    assert tarifs.taux_application(0.97) == -0.015
    assert tarifs.taux_application(1.0) == -0.0375


def test_majoration_cos_phi_appliquee_sur_energie():
    # cos phi ~ 0.71 -> majoration de 10 %
    sans = facturation.facture_speciale("MT-TG", 7100, 0, 100, redevance=0.0)
    avec = facturation.facture_speciale("MT-TG", 7100, 0, 100,
                                        energie_reactive=7042,
                                        redevance=0.0)
    fp = facturation.cos_phi(7100, 7042)
    assert 0.70 <= fp < 0.75
    majoration = 7100 * 85.29 * 0.10
    assert avec.montant_ht - sans.montant_ht == pytest.approx(majoration)


def test_comparaison_bt_classee():
    resultats = optimisation.comparer_bt(400, "domestique")
    assert len(resultats) == 4      # DPP et DMP, postpayé et Woyofal
    totaux = [r["total_ttc"] for r in resultats]
    assert totaux == sorted(totaux)
    assert resultats[0]["surcout"] == 0.0


def test_comparaison_bt_filtre_par_puissance():
    resultats = optimisation.comparer_bt(400, "domestique", ps_kw=10)
    assert {r["code"] for r in resultats} == {"DMP"}


def test_option_mt_recommandee():
    # 400 kW utilisés 3 000 h/an -> tarif général
    assert optimisation.option_mt_recommandee(400 * 3000, 400) == "MT-TG"
    assert optimisation.option_mt_recommandee(400 * 500, 400) == "MT-TCU"
    assert optimisation.option_mt_recommandee(400 * 5000, 400) == "MT-TLU"


def test_ps_optimale_sans_depassement_ni_gaspillage():
    # Pmax constante : l'optimum est exactement cette puissance
    resultat = optimisation.ps_optimale("MT-TG", [300] * 12, ps_min=250,
                                        ps_max=400, pas=1.0)
    assert resultat["ps_optimale"] == pytest.approx(300, abs=1)


def test_deplacement_pointe_reduit_la_facture():
    r = optimisation.deplacement_pointe("MT-TG", 50000, 20000, 300, 0.5)
    assert r["kwh_deplaces"] == pytest.approx(10000)
    assert r["economie_mensuelle"] > 0
    # L'énergie totale est conservée
    assert r["facture_apres"].energie_kwh == pytest.approx(70000)


def test_correction_cos_phi_gain_positif():
    r = optimisation.correction_cos_phi("MT-TG", 40000, 10000, 300, 60000)
    assert r["cos_phi_actuel"] < 0.80
    assert r["economie_annuelle"] > 0
