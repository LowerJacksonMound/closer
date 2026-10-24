## task-01. Split a bill with a tip

Add `tally.split_bill(amount, people, tip_percent=0)` to `tally.py`: what each person pays when a bill is split
equally after adding a tip.

**Acceptance criteria**
- The tip is `amount * tip_percent / 100`, added to the amount before splitting. The result is each person's share,
  rounded to cents: `split_bill(100, 4)` is `25.0`; `split_bill(100, 4, 20)` is `30.0`; `split_bill(10, 3)` is `3.33`.
- `people` must be a positive int: `0`, a negative number or a non-int raises `ValueError` whose message contains `people`.
- `tip_percent` must not be negative: a negative tip raises `ValueError` whose message contains `tip_percent`.
- A tip of `0` gives the same result as `share(amount, people)`.
- Tests in `tests/test_tally.py` for each case above.
