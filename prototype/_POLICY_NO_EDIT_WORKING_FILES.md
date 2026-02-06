# POLICY: No Direct Edit on Working Files

Rule:
- prototype/shoonya_adapter_v3.py is frozen
- changes must be made in new file:
  shoonya_adapter_v4.py, shoonya_adapter_v5.py...

Same rule for:
- main runner modules
- config
- indicators

Why:
To avoid corruption/mixed code + allow rollback.