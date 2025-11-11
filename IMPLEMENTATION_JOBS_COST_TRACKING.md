# Jobs and ProviderModels Extension - Implementation Documentation

## Overview

This document describes the implementation of token tracking and cost calculation features for the KIGate API system.

## Issue Requirements

The original issue (in German) requested:

1. **Output Tokens for Jobs**: Track the number of tokens returned by the AI (output tokens), in addition to existing input tokens
2. **Pricing for Provider Models**: Store prices per 1 million tokens for both input and output
3. **Cost Display**: Calculate and display approximate costs in the jobs UI with 4 decimal places
4. **Note**: API Users UI for TPM/RPM/current month tokens was mentioned as still needed (separate issue)

## Implementation Details

### 1. Database Schema Changes

#### Job Model (`model/job.py`)
```python
# Added field:
output_token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
```

#### ProviderModel (`model/provider.py`)
```python
# Added fields:
input_price_per_million: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
output_price_per_million: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
```

### 2. Database Migration (`database.py`)

Added automatic migration in `migrate_database_schema()` function:
- Adds `output_token_count` column to `jobs` table if missing
- Adds `input_price_per_million` column to `provider_models` table if missing
- Adds `output_price_per_million` column to `provider_models` table if missing

Migration is safe to run multiple times and handles both fresh and existing databases.

### 3. Service Layer Updates

#### JobService (`service/job_service.py`)

**New Method:**
```python
@classmethod
async def update_job_output_token_count(cls, db: AsyncSession, job_id: str, output_token_count: int) -> bool:
    """Update job output token count"""
```

**Updated Methods:**
- `create_job()`: Now accepts and stores `output_token_count`
- `get_jobs_paginated()`: Returns jobs with `output_token_count` field

#### ProviderService (`service/provider_service.py`)

**Updated Methods:**
- `create_provider_model()`: Now accepts and stores pricing fields
- Model creation and updates support pricing information

### 4. Admin Routes (`admin_routes.py`)

**New Helper Function:**
```python
async def _enrich_jobs_with_costs(db: AsyncSession, jobs: list):
    """
    Enrich jobs with cost information based on token counts and model pricing.
    Adds 'estimated_cost' field to each job dict.
    """
```

**Cost Calculation Formula:**
```
cost = (input_tokens / 1,000,000 × input_price_per_million) + 
       (output_tokens / 1,000,000 × output_price_per_million)
```

**Integration:**
- `admin_jobs()` route now calls `_enrich_jobs_with_costs()` before rendering
- Costs are calculated dynamically based on current model pricing
- Jobs without pricing information show `None` for cost

### 5. UI Updates (`templates/jobs.html`)

**New Table Columns:**

| Column | Display Name | Format | Example |
|--------|-------------|--------|---------|
| Input Tokens | Input Tokens | Thousands separator | 150,000 |
| Output Tokens | Output Tokens | Thousands separator | 75,000 |
| Estimated Cost | Ca. Kosten | 4 decimal places + € | 9.0000 € |

**Template Logic:**
- Shows formatted token counts with thousands separators
- Displays costs with exactly 4 decimal places
- Shows "-" for missing data with tooltip for models without pricing
- Green color (`text-success`) for cost values

### 6. API Models Updates

**JobCreate Pydantic Model:**
```python
class JobCreate(BaseModel):
    # ... existing fields ...
    output_token_count: Optional[int] = None
```

**JobResponse Pydantic Model:**
```python
class JobResponse(BaseModel):
    # ... existing fields ...
    output_token_count: Optional[int] = None
```

**ProviderModelCreate/Update/Response:**
```python
class ProviderModelCreate(BaseModel):
    # ... existing fields ...
    input_price_per_million: Optional[float] = None
    output_price_per_million: Optional[float] = None
```

## Usage Examples

### Creating a Provider Model with Pricing

```python
from model.provider import ProviderModelCreate
from service.provider_service import ProviderService

model_data = ProviderModelCreate(
    provider_id="provider-id",
    model_name="GPT-4",
    model_id="gpt-4",
    is_active=True,
    input_price_per_million=30.0,   # $30 per 1M input tokens
    output_price_per_million=60.0   # $60 per 1M output tokens
)

model = await ProviderService.create_provider_model(db, model_data)
```

### Creating a Job with Token Counts

```python
from model.job import JobCreate
from service.job_service import JobService

job_data = JobCreate(
    name="AI Query",
    user_id="user-123",
    provider="openai",
    model="gpt-4",
    status="completed",
    token_count=100_000,        # Input tokens
    output_token_count=50_000   # Output tokens
)

job = await JobService.create_job(db, job_data)
```

### Updating Output Tokens After Job Completion

```python
# When job completes, update output token count
success = await JobService.update_job_output_token_count(
    db, 
    job_id="job-123", 
    output_token_count=75_000
)
```

## Cost Calculation Examples

### Example 1: GPT-4 Query
- **Model Pricing**: $30/1M input, $60/1M output
- **Input Tokens**: 100,000
- **Output Tokens**: 50,000
- **Cost Calculation**:
  - Input: (100,000 / 1,000,000) × 30 = 3.0
  - Output: (50,000 / 1,000,000) × 60 = 3.0
  - **Total: 6.0000 €**

### Example 2: GPT-3.5 Turbo Query
- **Model Pricing**: $0.5/1M input, $1.5/1M output
- **Input Tokens**: 200,000
- **Output Tokens**: 100,000
- **Cost Calculation**:
  - Input: (200,000 / 1,000,000) × 0.5 = 0.1
  - Output: (100,000 / 1,000,000) × 1.5 = 0.15
  - **Total: 0.2500 €**

## Edge Cases Handled

1. **Jobs without pricing information**: Cost displays as "-" with tooltip
2. **Jobs without output tokens yet**: Output tokens display as "-"
3. **Processing jobs**: Only input tokens shown until completion
4. **Missing token counts**: Treated as 0 for cost calculation
5. **Models without pricing**: Cost is `None` and displayed as "-"

## Testing

### Test Coverage

**Existing Tests (8)** - All passing:
- `test_jobs_extension.py`: Jobs filtering, pagination, user display

**New Tests (9)** - All passing:
- `test_jobs_cost_calculation.py`:
  - Job creation with output tokens
  - Output token count updates
  - Cost calculation with various pricing scenarios
  - Edge cases (no pricing, missing tokens, etc.)
  - Provider model pricing operations

**Total: 17/17 tests passing**

### Running Tests

```bash
# Run all job-related tests
pytest test_jobs_extension.py test_jobs_cost_calculation.py -v

# Run specific test
pytest test_jobs_cost_calculation.py::test_cost_calculation_with_pricing -v
```

## Security Considerations

- ✅ All input is properly validated through Pydantic models
- ✅ SQL injection prevented by using SQLAlchemy ORM
- ✅ No sensitive data exposed in costs (only aggregated pricing)
- ✅ CodeQL security scan: 0 alerts

## Performance Considerations

1. **Cost Calculation**: Performed in memory after fetching jobs
2. **Database Query**: Single query to fetch all provider models with pricing
3. **Lookup Efficiency**: Uses dictionary for O(1) model price lookups
4. **Minimal Overhead**: Only adds calculation for jobs being displayed (25 per page)

## Migration Path

### For Existing Databases

1. **Automatic Migration**: Runs on application startup
2. **Backward Compatible**: New columns are nullable
3. **No Data Loss**: Existing jobs remain functional
4. **Graceful Degradation**: Missing pricing shows "-" instead of errors

### For New Installations

- All tables created with new schema automatically
- No manual migration needed

## Future Enhancements

Potential improvements for future iterations:

1. **Currency Conversion**: Support multiple currencies beyond €
2. **Bulk Cost Reports**: Add summary reports for cost analysis
3. **Cost Alerts**: Notify when jobs exceed cost thresholds
4. **Historical Pricing**: Track pricing changes over time
5. **Cost Projections**: Estimate costs before running jobs

## Related Files

- `model/job.py` - Job model definition
- `model/provider.py` - Provider and ProviderModel definitions
- `service/job_service.py` - Job business logic
- `service/provider_service.py` - Provider business logic
- `admin_routes.py` - Admin UI routes and cost calculation
- `templates/jobs.html` - Jobs display template
- `database.py` - Database setup and migrations
- `test_jobs_cost_calculation.py` - Test suite

## Support

For issues or questions about this implementation:
1. Check test files for usage examples
2. Review this documentation
3. Consult the original issue for requirements context

---

**Implementation Date**: November 11, 2025  
**Version**: 1.0  
**Status**: ✅ Complete
