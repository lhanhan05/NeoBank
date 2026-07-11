INSERT INTO cards (id, account_id, token, card_number, expiration_month, expiration_year, cvv_hash, status)
VALUES
  ('aaaa1111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'tok_luke_4242', '4111111111114242', 11, 2028, 'cvvhash_luke_demo', 'ACTIVE'),
  ('bbbb2222-2222-2222-2222-222222222222', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'tok_jane_1881', '4000000000001881', 2, 2024, 'cvvhash_jane_demo', 'EXPIRED'),
  ('cccc3333-3333-3333-3333-333333333333', 'cccccccc-cccc-cccc-cccc-cccccccccccc', 'tok_bob_3005', '4000000000003005', 7, 2027, 'cvvhash_bob_demo', 'FROZEN');

INSERT INTO authorization_log (id, card_id, merchant, amount, approved, reason)
VALUES
  ('dddd4444-4444-4444-4444-444444444444', 'aaaa1111-1111-1111-1111-111111111111', 'Blue Bottle Coffee', 24.58, true, 'Approved valid card transaction'),
  ('eeee5555-5555-5555-5555-555555555555', 'bbbb2222-2222-2222-2222-222222222222', 'Online Subscription Co', 12.99, false, 'Declined because card is expired'),
  ('ffff6666-6666-6666-6666-666666666666', 'cccc3333-3333-3333-3333-333333333333', 'Electronics Depot', 199.99, false, 'Declined because card is frozen');
