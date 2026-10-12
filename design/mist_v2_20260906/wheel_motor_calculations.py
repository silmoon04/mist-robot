"""Regenerate wheel_motor_envelopes.json. Screening model, not a thermal validation."""

import json
from math import cos, pi, radians, sin
from pathlib import Path

G = 9.80665

MOTORS = [
    dict(id="owned_sts_direct", label="Feetech ST-3215-C018 direct", mass_kg=0.055,
         voltage_v=12, rpm_no_load=45, stall_torque_nm=30 * 0.0980665,
         stall_current_a=2.7, no_load_current_a=0.18,
         provisional_current_limit_a=0.9, maker_rated_torque_nm=10 * 0.0980665,
         speed_multiplier=1, transmission_efficiency=1,
         source="https://cdn.robotshop.com/media/F/Fit/RB-Fit-155/pdf/feetech_12v_30kg_cm_magnetic_encoding_servo_sts321_specification_pdf.pdf"),
    dict(id="owned_sts_speedup_7_5", label="Owned STS with hypothetical 7.5:1 speed increase",
         mass_kg=0.055, extra_transmission_mass_kg_range=[0.03, 0.06],
         voltage_v=12, rpm_no_load=45, stall_torque_nm=30 * 0.0980665,
         stall_current_a=2.7, no_load_current_a=0.18,
         provisional_current_limit_a=0.9, maker_rated_torque_nm=10 * 0.0980665,
         speed_multiplier=7.5, transmission_efficiency=0.85,
         source="https://cdn.robotshop.com/media/F/Fit/RB-Fit-155/pdf/feetech_12v_30kg_cm_magnetic_encoding_servo_sts321_specification_pdf.pdf"),
    dict(id="pololu_5214_n20_75", label="Pololu #5214 HPCB 12V 75:1 with encoder",
         mass_kg=0.011, voltage_v=12, rpm_no_load=450,
         stall_torque_nm=0.0980665, stall_current_a=0.75,
         no_load_current_a=0.08, provisional_current_limit_a=0.1875,
         speed_multiplier=1, transmission_efficiency=1,
         source="https://www.pololu.com/product/5214/specs"),
    dict(id="waveshare_n20_200", label="Waveshare DCGM-N20-12V-EN-200RPM",
         mass_kg=0.018, voltage_v=12, rpm_no_load=200,
         stall_torque_nm=1.2 * 0.0980665, stall_current_a=1.1,
         no_load_current_a=0.1, provisional_current_limit_a=0.275,
         speed_multiplier=1, transmission_efficiency=1,
         source="https://www.waveshare.com/wiki/DCGM-N20-12V-EN-200RPM"),
    dict(id="pololu_4843_25d_hp_20_4", label="Pololu #4843 25D HP 12V 20.4:1 encoder",
         mass_kg=0.098, voltage_v=12, rpm_no_load=500,
         stall_torque_nm=7.4 * 0.0980665, stall_current_a=5,
         no_load_current_a=0.3, provisional_current_limit_a=1.25,
         speed_multiplier=1, transmission_efficiency=1,
         source="https://www.pololu.com/product/4843/specs"),
    dict(id="dfrobot_fit0493", label="DFRobot FIT0493 25mm 12V 350rpm encoder",
         mass_kg=0.098, voltage_v=12, rpm_no_load=350,
         stall_torque_nm=12 * 0.0980665, stall_current_a=5.5,
         no_load_current_a=0.23, provisional_current_limit_a=1,
         speed_multiplier=1, transmission_efficiency=1,
         source="https://www.dfrobot.com/product-1462.html",
         caution="Maker maximum-efficiency data does not match an endpoint-linear current model; bench measure."),
]


def torque_required(mass, radius, acceleration=0, slope_deg=0, contacts=4, crr=0.03):
    angle = radians(slope_deg)
    force = mass * (acceleration + G * (sin(angle) + crr * cos(angle)))
    return force * radius / contacts


def operating_point(motor, torque_wheel, voltage, radius):
    k = motor["speed_multiplier"]
    efficiency = motor["transmission_efficiency"]
    torque_motor = torque_wheel * k / efficiency
    current = motor["no_load_current_a"] + (
        motor["stall_current_a"] - motor["no_load_current_a"]
    ) * torque_motor / motor["stall_torque_nm"]
    # Compare all options with <=12 V effective drive; do not overdrive 12 V DC motors.
    voltage_fraction = min(voltage, motor["voltage_v"]) / motor["voltage_v"]
    rpm = max(0, motor["rpm_no_load"] * (
        voltage_fraction - torque_motor / motor["stall_torque_nm"]
    )) * k
    current_limited_torque = motor["stall_torque_nm"] * max(0,
        (motor["provisional_current_limit_a"] - motor["no_load_current_a"])
        / (motor["stall_current_a"] - motor["no_load_current_a"])
    )
    cap_motor = min(current_limited_torque,
                    motor.get("maker_rated_torque_nm", float("inf")))
    cap_wheel = cap_motor * efficiency / k
    return dict(
        wheel_torque_required_nm=round(torque_wheel, 6),
        motor_torque_required_nm=round(torque_motor, 6),
        current_linear_estimate_a=round(current, 4),
        provisional_wheel_torque_cap_nm=round(cap_wheel, 6),
        torque_margin=round(cap_wheel / torque_wheel, 3),
        rpm_linear_estimate=round(rpm, 3),
        speed_linear_estimate_mps=round(rpm * 2 * pi * radius / 60, 4),
        within_provisional_current_limit=current <= motor["provisional_current_limit_a"],
        note="Speed is only an operating prediction when the current/torque limit also passes.",
    )


def main():
    cases = []
    scenarios = [
        ("flat_cruise", 0, 0, 4),
        ("flat_accel_1mps2", 1, 0, 4),
        ("slope_10deg_cruise", 0, 10, 4),
        ("slope_15deg_cruise", 0, 15, 4),
        ("slope_15deg_two_contacts", 0, 15, 2),
    ]
    for mass in (3, 3.5, 4):
        for diameter in (0.07, 0.085, 0.1):
            for voltage in (12.6, 12, 11.1, 10.5, 7.4, 5):
                for scenario, acceleration, slope, contacts in scenarios:
                    torque = torque_required(mass, diameter / 2, acceleration, slope, contacts)
                    for motor in MOTORS:
                        cases.append(dict(motor_id=motor["id"], mass_kg=mass,
                            wheel_diameter_m=diameter, battery_voltage_v=voltage,
                            scenario=scenario, driven_contacts=contacts,
                            **operating_point(motor, torque, voltage, diameter / 2)))
    result = dict(
        status="analytic screening only; no thermal, traction, gearbox or physical validation",
        date="2026-09-06",
        assumptions=dict(rolling_resistance_coefficient=0.03,
            load_distribution="equal across stated driven contacts",
            wheel_and_gear_inertia="excluded; add acceleration margin",
            voltage_scaling="linear no-load speed and stall torque, effective drive capped at12V",
            current_model="linear between nominal no-load and extrapolated stall endpoints",
            provisional_limit="screening ceiling, not certified continuous rating",
            actual_torque_speed_tolerance="not sampled; test motor-to-motor variation separately"),
        motors=MOTORS,
        cases=cases,
    )
    output = Path(__file__).with_name("wheel_motor_envelopes.json")
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(cases)} cases to {output.name}")
    for case in cases:
        if (case["mass_kg"] == 4 and case["wheel_diameter_m"] == 0.085
            and case["battery_voltage_v"] == 10.5 and case["scenario"] in
                ("flat_accel_1mps2", "slope_15deg_cruise")):
            print(case["motor_id"], case["scenario"],
                  case["wheel_torque_required_nm"], case["speed_linear_estimate_mps"],
                  case["within_provisional_current_limit"])


if __name__ == "__main__":
    main()
