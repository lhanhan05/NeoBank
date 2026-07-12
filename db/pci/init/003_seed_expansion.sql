INSERT INTO cards (id, account_id, token, card_number, expiration_month, expiration_year, cvv_hash, status)
VALUES
  ('dddd7777-7777-7777-7777-777777777777', 'dddddddd-aaaa-bbbb-cccc-111111111111', 'tok_maria_7711', '4111111111117711', 9, 2029, 'cvvhash_maria_demo', 'ACTIVE'),
  ('eeee8888-8888-8888-8888-888888888888', 'eeeeeeee-aaaa-bbbb-cccc-222222222222', 'tok_ethan_9090', '4000000000009090', 5, 2028, 'cvvhash_ethan_demo', 'ACTIVE')
ON CONFLICT (id) DO NOTHING;

INSERT INTO authorization_log (id, card_id, merchant, amount, approved, reason)
VALUES
  ('11117777-7777-7777-7777-777777777777', 'dddd7777-7777-7777-7777-777777777777', 'Whole Foods Market', 64.20, true, 'Approved everyday spending transaction'),
  ('22228888-8888-8888-8888-888888888888', 'eeee8888-8888-8888-8888-888888888888', 'TravelNow', 220.00, true, 'Approved merchant refund card match')
ON CONFLICT (id) DO NOTHING;
