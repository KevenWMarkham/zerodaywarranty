# Test fixtures

The reference dataset is generated deterministically at test time by
`zero_day_warranty.synthetic.generate()` (seed-pinned), so most tests need no
static fixtures. Add static fixtures here only for cases that cannot be produced
by the generator (e.g. a malformed manifest used to assert a validation error).
