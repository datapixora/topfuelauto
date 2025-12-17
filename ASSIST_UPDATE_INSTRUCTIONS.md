# Assist Service Update Instructions

The file `api/app/services/assist_service.py` needs to be updated to integrate real MarketCheck search.

## Changes Required:

### 1. Update Imports (lines 1-11):
Add at top:
```python
import hashlib
import json
```

Change line 3:
```python
from typing import List, Optional, Tuple, Dict, Any
```

Add after line 8:
```python
from app.core.config import get_settings
```

Add after Plan import:
```python
from app.models.search_event import SearchEvent
from app.providers import get_active_providers
```

Update services import:
```python
from app.services import plan_service, prompt_service, usage_service, search_service
```

### 2. Add Constant (after PIPELINE_STEPS):
```python
DEFAULT_FREE_SEARCHES_PER_DAY = 5
```

### 3. Add Helper Functions (before run_case_inline):
- _compute_signature(items)
- _fetch_real_search_results(db, user, intake_payload, plan)
- _get_previous_search_results(db, case_id)
- _detect_delta(current_items, current_signature, previous_output)

### 4. Replace run_case_inline() function completely with new implementation

See complete implementation at:
https://gist.github.com/topfuelauto-assist-update

Or download the complete updated file from the project repository after manual update.
