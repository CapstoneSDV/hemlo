# SecOC Cryptographic Parameter Downgrade (FM-1 Known Gap)

**Source:** AUTOSAR SecOC Specification; evaluation of boolean authentication boundary

**Summary:** Update preserves SECURED-I-PDU wrapper but truncates MAC to 8 bits and clears freshness. Expected: PASS (demonstrates the documented boolean-SecOC limitation).

**Expected verdict on the update (before -> after):** PASS
