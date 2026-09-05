# Extending a Product Vertical

## The plain-language version

The advisor is not hard-coded to recommend computers, but each category needs its own definition of a good decision. A laptop display, an HVAC compressor, an insurance policy, and a managed service do not share meaningful specifications just because all four can be sold.

To add a vertical, keep the common identity and evidence envelope, then define only the specifications, questions, constraints, services, and preferences that matter to that category.

## Extension checklist

1. Choose one narrow customer decision, not an entire industry.
2. Define product identity: make, model, model number, version, and configuration.
3. Define the vertical specification object.
4. Define the customer intake fields that can establish requirements.
5. Separate hard feasibility constraints from weighted preferences.
6. Add next questions for material missing facts.
7. Define services that reduce implementation or outcome risk.
8. Add source, date, scope, and confidence to product evidence.
9. Create at least three synthetic scenarios, including one with no viable answer.
10. Have domain experts challenge failures, rankings, and missing questions.

## Example: workstation specification object

```json
{
  "form_factor": "laptop",
  "cpu": {"make": "...", "model": "...", "cores": 16, "threads": 32},
  "gpu": {"make": "...", "model": "...", "vram_gb": 16, "memory_type": "GDDR7"},
  "memory": {"capacity_gb": 64, "type": "DDR5", "speed_mt_s": 5600, "ecc": false},
  "storage": {
    "total_capacity_tb": 2,
    "primary": {"capacity_tb": 2, "type": "NVMe SSD", "interface": "PCIe 4.0"}
  },
  "power": {"max_draw_w": 280},
  "display": {
    "size_inches": 16,
    "panel_type": "OLED",
    "resolution_width": 3840,
    "resolution_height": 2400,
    "refresh_hz": 120,
    "brightness_nits": 500,
    "color_gamut_dci_p3_percent": 100
  }
}
```

## Example: unrelated vertical

A commercial cooling system might use:

```json
{
  "capacity_tons": 20,
  "efficiency": {"ieer": 18.2},
  "refrigerant": "example-refrigerant",
  "electrical": {"voltage": 460, "phase": 3},
  "dimensions_mm": {"width": 2200, "depth": 900, "height": 1800},
  "ambient_operating_range_c": {"minimum": -20, "maximum": 52},
  "controls": ["BACnet"],
  "sound_db": 76
}
```

The shared engine can compare numeric, categorical, and set-valued facts, but domain experts must define what constitutes failure and what merely affects preference.

## Rule quality questions

For every proposed rule, ask:

- Is this truly a hard constraint?
- Which intake fact establishes the requirement?
- Which product fact proves compliance?
- What happens if either fact is missing?
- Does the rule apply to every product subtype?
- Is the source current and specific to this model number?
- Can a human understand the failure message?
- What representative case would prove this rule wrong?

If those questions cannot be answered, the rule is not ready to automate.
