"""Write a short text companion from the final, unchanged physics report."""
import json
from pathlib import Path

directory=Path(__file__).resolve().parent/"output"
report=json.loads((directory/"simulation_report.json").read_text())
obs=report["observed"]
text=f"""QUADRUPED SIMULATION RESULT

Status: {report['status']}
Calculated assembly mass: {report['mass_kg']:.6f} kg
Duration: {obs['simulated_seconds']:.1f} simulated seconds
Motion: free-base standing, one full phone turn, one slow crawl cycle
Phone orientation: landscape, with the screen plane vertical
Body advance: {obs['advance_x_mm']:.3f} mm
Maximum sampled roll or pitch: {obs['max_roll_pitch_deg']:.3f} degrees
Minimum sampled mid-swing COM support margin: {obs['minimum_mid_swing_margin_mm']:.3f} mm
Maximum sampled stance-foot position error: {obs['maximum_stance_error_mm']:.3f} mm
Peak quasi-static joint load: {max(obs['static_peak_joint_torque_nm'].values()):.6f} Nm
Peak sampled commanded joint torque: {max(obs['dynamic_peak_joint_torque_nm'].values()):.6f} Nm
Applied torque cap: {report['parameters']['effort_cap_nm']:.3f} Nm
Phone travel: {report['controller_tracking']['phone_travel_deg']:.3f} degrees
Maximum sampled phone tracking error: {report['controller_tracking']['maximum_phone_error_deg']:.4f} degrees

The solver and torque cap run at 240 Hz. Reported trajectory and contact metrics
are sampled at 20 Hz. There is no fixed base or external base constraint.

This is a bounded simulation result. The finite PD and gravity-compensation
actuation model is not bench calibrated against STS3215 internal firmware.
Mapping its torques and positions to real servo commands remains unvalidated.
No controller has been deployed. Physical fit and hardware walking are untested.

The modeled foot is a 14 mm wide, 5 mm radius rocker cylinder. It approximates
the actual small neutral flat within 0.2 mm. Friction and controller gains are
assumed, and the run does not qualify printed strength, cable behavior or heat.

The phone uses WiFi and its internal battery while panning. Disconnect USB
before rotation. Charge only while parked.

Manifest SHA256: {report['inputs']['manifest_sha256']}
URDF SHA256: {report['inputs']['urdf_sha256']}
Inputs unchanged during the run: {report['inputs']['unchanged_during_run']}
"""
(directory/"simulation_notes.txt").write_text(text,encoding="utf-8")
print(str(directory/"simulation_notes.txt"))
