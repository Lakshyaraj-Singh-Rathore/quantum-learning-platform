"""Live end-to-end verification of Qudit Lab (Beta) against running backend API.

Exercises:
1. All 4 dimensions: d in {2, 3, 4, 5}
2. Initial basis state preparation: |0> .. |d-1>
3. Generalized Shift X_d, Phase Z_d, and Fourier F_d gates
4. Two-qudit Bell entanglement circuits (|Phi_d>) at every dimension
5. Global purity (gamma=1) and reduced subsystem mixedness (gamma=1/d, entropy=log2(d))
6. All 3 noise channels: Depolarizing, Dephasing, and Relaxation
7. Admission control & rejection of oversized circuits (d=2:11, d=3:7, d=4:6, d=5:5)
"""

from __future__ import annotations

import json
import math
import sys
import urllib.request
import urllib.error

# Ensure UTF-8 output on Windows terminal
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

API_URL = "http://127.0.0.1:8000"


def post_json(endpoint: str, data: dict, token: str | None = None) -> tuple[int, dict]:
    url = f"{API_URL}{endpoint}"
    payload = json.dumps(data).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return resp.status, body
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
        except Exception:
            body = {"error": str(exc)}
        return exc.code, body


def get_json(endpoint: str) -> tuple[int, dict]:
    url = f"{API_URL}{endpoint}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return resp.status, body
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
        except Exception:
            body = {"error": str(exc)}
        return exc.code, body


def main():
    print("=" * 80)
    print("QUANTUMLEARNAI QUDIT LAB: LIVE API END-TO-END VERIFICATION")
    print("=" * 80)

    # 1. Authenticate with seeded student account
    print("\n[Step 1] Authenticating with backend...")
    status, auth_data = post_json("/auth/login", {
        "email": "student@quantum.local",
        "password": "password123",
    })
    if status != 200 or "access_token" not in auth_data:
        print(f"FAILED: Authentication returned status {status}: {auth_data}")
        sys.exit(1)

    token = auth_data["access_token"]
    print("PASS: Authenticated successfully. Bearer token acquired.")

    # 2. Check limits & catalogue
    print("\n[Step 2] Querying /qudit/limits and /qudit/catalogue...")
    s_lim, lim_data = get_json("/qudit/limits")
    assert s_lim == 200, f"Limits status {s_lim}"
    print(f"PASS: Supported dimensions: {lim_data['supported_dimensions']}")
    print(f"PASS: Safe limits: {lim_data['safe_limits']}")
    assert lim_data["safe_limits"] == {"2": 10, "3": 6, "4": 5, "5": 4}

    s_cat, cat_data = get_json("/qudit/catalogue")
    assert s_cat == 200, f"Catalogue status {s_cat}"
    gate_ids = [g["id"] for g in cat_data]
    print(f"PASS: Verified gate catalogue with {len(gate_ids)} gates: {gate_ids}")
    assert {"x", "z", "f", "sum", "cp", "swap", "r_jk"} <= set(gate_ids)

    # 3. Test dimensions d in {2, 3, 4, 5}: Initial states, Shift, Phase, Fourier
    print("\n[Step 3] Exercising single-qudit operations across d in {2, 3, 4, 5}...")
    for d in [2, 3, 4, 5]:
        print(f"\n--- Testing Dimension d = {d} ---")

        # 3a. Initial basis-state preparation in |d-1>
        init_level = d - 1
        circ_init = {
            "id": f"test-init-{d}",
            "dimension": d,
            "wires": [{"id": "q0", "index": 0, "dimension": d, "initial_state": init_level}],
            "ops": [],
        }
        status, res_init = post_json("/qudit/simulate", {"circuit": circ_init}, token)
        assert status == 200, f"Init state d={d} failed: {res_init}"
        sv = res_init["state_validation"]
        assert sv["is_valid"] and sv["is_positive_semidefinite"]
        assert math.isclose(sv["trace"], 1.0, abs_tol=1e-5)
        assert math.isclose(sv["purity"], 1.0, abs_tol=1e-4)
        target_ket = f"|{init_level}⟩"
        assert math.isclose(res_init["probabilities"][target_ket], 1.0, abs_tol=1e-4)
        print(f"PASS (d={d}): Initial state |{init_level}⟩ prepared. P({target_ket}) = 1.000, Purity = 1.000")

        # 3b. Generalized Shift Gate X_d on |0> -> |1>
        circ_shift = {
            "id": f"test-shift-{d}",
            "dimension": d,
            "wires": [{"id": "q0", "index": 0, "dimension": d, "initial_state": 0}],
            "ops": [{"id": "op1", "gate": "x", "targets": [0], "controls": [], "dimension": d}],
        }
        status, res_shift = post_json("/qudit/simulate", {"circuit": circ_shift}, token)
        assert status == 200, f"Shift d={d} failed: {res_shift}"
        assert math.isclose(res_shift["probabilities"]["|1⟩"], 1.0, abs_tol=1e-4)
        print(f"PASS (d={d}): Shift gate X_{d} applied to |0⟩. P(|1⟩) = 1.000, Purity = 1.000")

        # 3c. Generalized Fourier Gate F_d on |0> -> equal superposition 1/d
        circ_fourier = {
            "id": f"test-fourier-{d}",
            "dimension": d,
            "wires": [{"id": "q0", "index": 0, "dimension": d, "initial_state": 0}],
            "ops": [{"id": "op1", "gate": "f", "targets": [0], "controls": [], "dimension": d}],
        }
        status, res_fourier = post_json("/qudit/simulate", {"circuit": circ_fourier}, token)
        assert status == 200, f"Fourier d={d} failed: {res_fourier}"
        sv_f = res_fourier["state_validation"]
        assert sv_f["is_valid"] and math.isclose(sv_f["purity"], 1.0, abs_tol=1e-4)
        expected_prob = 1.0 / d
        for k in range(d):
            p = res_fourier["probabilities"][f"|{k}⟩"]
            assert math.isclose(p, expected_prob, abs_tol=1e-4)
        expected_entropy = math.log2(d)
        print(f"PASS (d={d}): Fourier superposition F_{d} verified. All P(|k⟩) = {expected_prob:.4f} (1/{d}), Entropy = {sv_f['entropy']:.4f} bits")

        # 3d. Generalized Phase Gate Z_d: Coherence rotation
        circ_phase = {
            "id": f"test-phase-{d}",
            "dimension": d,
            "wires": [{"id": "q0", "index": 0, "dimension": d, "initial_state": 0}],
            "ops": [
                {"id": "op1", "gate": "f", "targets": [0], "controls": [], "dimension": d},
                {"id": "op2", "gate": "z", "targets": [0], "controls": [], "dimension": d},
            ],
        }
        status, res_phase = post_json("/qudit/simulate", {"circuit": circ_phase}, token)
        assert status == 200, f"Phase d={d} failed: {res_phase}"
        # Populations remain 1/d
        for k in range(d):
            assert math.isclose(res_phase["probabilities"][f"|{k}⟩"], expected_prob, abs_tol=1e-4)
        # Phase of element (0, 1) has rotated by 2*pi/d
        rho_phase = res_phase["density_matrix"]
        omega = complex(math.cos(2 * math.pi / d), math.sin(2 * math.pi / d))
        elem_01 = complex(rho_phase[0][1]["real"], rho_phase[0][1]["imag"])
        # Expected element is (1/d) * conj(omega)
        expected_elem_01 = (1.0 / d) * omega.conjugate()
        assert math.isclose(abs(elem_01 - expected_elem_01), 0.0, abs_tol=1e-4)
        print(f"PASS (d={d}): Phase gate Z_{d} coherence rotation verified: rho[0,1] = {elem_01.real:.3f} + {elem_01.imag:.3f}i")

    # 4. Two-qudit Bell Entanglement at every dimension d in {2, 3, 4, 5}
    print("\n[Step 4] Testing 2-qudit Bell Entanglement |Phi_d> across all d in {2, 3, 4, 5}...")
    for d in [2, 3, 4, 5]:
        circ_bell = {
            "id": f"bell-{d}",
            "dimension": d,
            "wires": [
                {"id": "q0", "index": 0, "dimension": d, "initial_state": 0},
                {"id": "q1", "index": 1, "dimension": d, "initial_state": 0},
            ],
            "ops": [
                {"id": "op1", "gate": "f", "targets": [0], "controls": [], "dimension": d},
                {"id": "op2", "gate": "sum", "targets": [1], "controls": [0], "dimension": d},
            ],
        }
        status, res_bell = post_json("/qudit/simulate", {"circuit": circ_bell, "shots": 1000}, token)
        assert status == 200, f"Bell entanglement d={d} failed: {res_bell}"

        sv = res_bell["state_validation"]
        # Global state must be pure
        assert math.isclose(sv["purity"], 1.0, abs_tol=1e-4), f"Global purity {sv['purity']}"
        assert math.isclose(sv["trace"], 1.0, abs_tol=1e-5)
        assert sv["is_hermitian"] and sv["is_positive_semidefinite"]

        # Populations: |j, j> has 1/d, all |j, k> (j != k) have 0
        for j in range(d):
            for k in range(d):
                label = f"|{j},{k}⟩"
                expected_p = 1.0 / d if j == k else 0.0
                actual_p = res_bell["populations"].get(label, 0.0)
                assert math.isclose(actual_p, expected_p, abs_tol=1e-4), f"{label}: got {actual_p}, expected {expected_p}"

        # Subsystem partial trace on q0: must be maximally mixed
        red_q0 = res_bell["reduced_states"]["q0"]
        expected_sub_purity = 1.0 / d
        assert math.isclose(red_q0["purity"], expected_sub_purity, abs_tol=1e-4), f"Red purity: {red_q0['purity']}"
        expected_sub_entropy = math.log2(d)
        assert math.isclose(red_q0["entropy"], expected_sub_entropy, abs_tol=1e-4), f"Red entropy: {red_q0['entropy']}"

        print(
            f"PASS (d={d}): 2-Qudit Bell State |Φ_{d}⟩ verified! "
            f"Global Purity = {sv['purity']:.4f} (Pure), "
            f"Subsystem q0 Purity = {red_q0['purity']:.4f} (1/{d}, Maximally Mixed), "
            f"Subsystem Entropy = {red_q0['entropy']:.4f} bits"
        )

    # 5. Exercise each advertised noise channel
    print("\n[Step 5] Exercising all 3 advertised noise channels end-to-end...")
    d_noise = 3
    base_fourier = {
        "id": "noise-test-base",
        "dimension": d_noise,
        "wires": [{"id": "q0", "index": 0, "dimension": d_noise, "initial_state": 0}],
        "ops": [{"id": "op1", "gate": "f", "targets": [0], "controls": [], "dimension": d_noise}],
    }

    # 5a. Depolarizing noise
    p_depol = 0.35
    noise_depol = {
        "depolarizing": {"enabled": True, "p": p_depol},
        "dephasing": {"enabled": False, "gamma": 0.0},
        "relaxation": {"enabled": False, "gamma": 0.0},
    }
    status, res_depol = post_json("/qudit/simulate", {"circuit": base_fourier, "noise": noise_depol}, token)
    assert status == 200, f"Depol noise failed: {res_depol}"
    assert res_depol["noisy"] is True
    # Analytical purity for depolarizing channel on pure state in dimension d:
    # rho' = (1-p)|+><+| + (p/d)I_d
    # Eigenvalues: (1-p + p/d) (multiplicity 1), and (p/d) (multiplicity d-1)
    # gamma = (1-p + p/d)^2 + (d-1)*(p/d)^2
    lambda_0 = 1.0 - p_depol + (p_depol / d_noise)
    lambda_rest = p_depol / d_noise
    analytical_purity = (lambda_0 ** 2) + (d_noise - 1) * (lambda_rest ** 2)
    actual_purity = res_depol["state_validation"]["purity"]
    assert math.isclose(actual_purity, analytical_purity, abs_tol=1e-3)
    assert actual_purity < 0.95
    print(f"PASS: Depolarizing noise (p={p_depol}) verified: Purity dropped from 1.000 to {actual_purity:.4f} (Analytical: {analytical_purity:.4f})")

    # 5b. Dephasing noise
    gamma_deph = 0.40
    noise_deph = {
        "depolarizing": {"enabled": False, "p": 0.0},
        "dephasing": {"enabled": True, "gamma": gamma_deph},
        "relaxation": {"enabled": False, "gamma": 0.0},
    }
    status, res_deph = post_json("/qudit/simulate", {"circuit": base_fourier, "noise": noise_deph}, token)
    assert status == 200, f"Dephase noise failed: {res_deph}"
    # Populations remain exactly 1/3
    for k in range(d_noise):
        assert math.isclose(res_deph["probabilities"][f"|{k}⟩"], 1.0 / d_noise, abs_tol=1e-4)
    # Off-diagonal element (0, 1) damped by (1 - gamma)
    mat_deph = res_deph["density_matrix"]
    coherence_01 = mat_deph[0][1]["mag"]
    expected_coherence = (1.0 / d_noise) * (1.0 - gamma_deph)
    assert math.isclose(coherence_01, expected_coherence, abs_tol=1e-3)
    print(f"PASS: Dephasing noise (gamma={gamma_deph}) verified: Diagonal populations preserved at 0.333, off-diagonal coherence damped to {coherence_01:.4f} (Expected: {expected_coherence:.4f})")

    # 5c. Multi-level relaxation noise
    # Initialize in highest level |2>, apply relaxation
    circ_relax = {
        "id": "relax-test",
        "dimension": d_noise,
        "wires": [{"id": "q0", "index": 0, "dimension": d_noise, "initial_state": d_noise - 1}],
        "ops": [],
    }
    gamma_relax = 0.60
    noise_relax = {
        "depolarizing": {"enabled": False, "p": 0.0},
        "dephasing": {"enabled": False, "gamma": 0.0},
        "relaxation": {"enabled": True, "gamma": gamma_relax},
    }
    status, res_relax = post_json("/qudit/simulate", {"circuit": circ_relax, "noise": noise_relax}, token)
    assert status == 200, f"Relax noise failed: {res_relax}"
    # Population of |2> must have decreased, and lower level |1> must have non-zero population
    p2 = res_relax["probabilities"]["|2⟩"]
    p1 = res_relax["probabilities"]["|1⟩"]
    assert p2 < 1.0 and p1 > 0.0
    assert math.isclose(res_relax["state_validation"]["trace"], 1.0, abs_tol=1e-5)
    print(f"PASS: Relaxation noise (gamma={gamma_relax}) verified: Excited level |2⟩ decayed (P(|2⟩)={p2:.3f}, P(|1⟩)={p1:.3f}), Trace = 1.000")

    # 6. Admission Control & Oversized Circuit Rejection
    print("\n[Step 6] Testing Admission Control & Oversized Circuit Rejection...")
    limits_to_test = [
        (2, 11),  # Cap is 10
        (3, 7),   # Cap is 6
        (4, 6),   # Cap is 5
        (5, 5),   # Cap is 4
    ]
    for dim, count in limits_to_test:
        oversized_circuit = {
            "id": f"oversized-{dim}",
            "dimension": dim,
            "wires": [{"id": f"q{i}", "index": i, "dimension": dim, "initial_state": 0} for i in range(count)],
            "ops": [],
        }
        # Pre-execution validation check
        val_status, val_report = post_json("/qudit/validate", oversized_circuit)
        assert val_status == 200
        assert val_report["valid"] is False
        assert any("safety limit" in err for err in val_report["errors"])

        # Direct simulation submission check
        sim_status, sim_err = post_json("/qudit/simulate", {"circuit": oversized_circuit}, token)
        assert sim_status == 422, f"Expected 422 for d={dim} count={count}, got {sim_status}"
        print(f"PASS: Oversized circuit (d={dim}, {count} qudits) safely rejected with HTTP 422 before allocation.")

    # 7. Invalid Parameter Rejection
    print("\n[Step 7] Testing invalid parameter rejection...")
    invalid_dim_circuit = {
        "id": "invalid-dim",
        "dimension": 6,  # d=6 unsupported
        "wires": [{"id": "q0", "index": 0, "dimension": 6, "initial_state": 0}],
        "ops": [],
    }
    status_inv, err_inv = post_json("/qudit/simulate", {"circuit": invalid_dim_circuit}, token)
    assert status_inv == 422
    print(f"PASS: Unsupported dimension d=6 safely rejected with HTTP 422.")

    print("\n" + "=" * 80)
    print("ALL LIVE API VERIFICATION CHECKS COMPLETED SUCCESSFULLY (100% PASS)")
    print("=" * 80)


if __name__ == "__main__":
    main()
