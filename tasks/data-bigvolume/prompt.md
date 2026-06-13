`events.csv` in the current directory is a large event log with ~150,000 rows
and columns: event_id, date (YYYY-MM-DD in 2025), user_id, country,
event_type, amount_cents. `amount_cents` is an integer amount in cents and is
0 for every event_type other than `purchase`. Revenue means the sum of
`amount_cents`.

Answer these questions exactly, in your final reply:
1. Which country generated the most total revenue?
2. Which event_type is the most frequent overall?
3. Which calendar month had the highest total revenue?
4. How many individual events had amount_cents strictly greater than 50000
   (i.e. more than $500)? (exact count)
