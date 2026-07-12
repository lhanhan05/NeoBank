INSERT INTO customers (id, first_name, last_name, email, phone, date_of_birth, address)
VALUES
  ('44444444-4444-4444-4444-444444444444', 'Maria', 'Garcia', 'maria.garcia@example.com', '555-0104', '1991-06-28', '404 Castro Street, Mountain View, CA'),
  ('55555555-5555-5555-5555-555555555555', 'Ethan', 'Lee', 'ethan.lee@example.com', '555-0105', '1985-11-14', '505 Grand Avenue, Berkeley, CA')
ON CONFLICT (id) DO NOTHING;

INSERT INTO accounts (id, customer_id, account_number, account_type, balance, currency, status, card_token)
VALUES
  ('dddddddd-aaaa-bbbb-cccc-111111111111', '44444444-4444-4444-4444-444444444444', 'CHK-1000004', 'checking', 3421.77, 'USD', 'ACTIVE', 'tok_maria_7711'),
  ('eeeeeeee-aaaa-bbbb-cccc-222222222222', '55555555-5555-5555-5555-555555555555', 'CHK-1000005', 'checking', 2890.64, 'USD', 'ACTIVE', 'tok_ethan_9090')
ON CONFLICT (id) DO NOTHING;

INSERT INTO transactions (id, account_id, amount, currency, transaction_type, merchant_name, description, status)
VALUES
  ('aaaa0000-0000-0000-0000-000000000004', 'dddddddd-aaaa-bbbb-cccc-111111111111', 64.20, 'USD', 'purchase', 'Whole Foods Market', 'Weekly groceries', 'approved'),
  ('aaaa0000-0000-0000-0000-000000000005', 'dddddddd-aaaa-bbbb-cccc-111111111111', 12.49, 'USD', 'purchase', 'Caltrain', 'Transit reload', 'approved'),
  ('aaaa0000-0000-0000-0000-000000000006', 'eeeeeeee-aaaa-bbbb-cccc-222222222222', 18.75, 'USD', 'purchase', 'Local Pharmacy', 'Prescription pickup', 'approved'),
  ('aaaa0000-0000-0000-0000-000000000007', 'eeeeeeee-aaaa-bbbb-cccc-222222222222', 220.00, 'USD', 'refund', 'TravelNow', 'Travel refund after cancellation', 'approved')
ON CONFLICT (id) DO NOTHING;

INSERT INTO support_tickets (id, customer_id, subject, body, status)
VALUES
  ('11111111-aaaa-bbbb-cccc-333333333333', '44444444-4444-4444-4444-444444444444', 'Debit card replacement after wear', 'My debit card chip has become unreliable at checkout. Please help me replace the card when possible.', 'open'),
  ('22222222-aaaa-bbbb-cccc-444444444444', '55555555-5555-5555-5555-555555555555', 'Request for courtesy refund', 'A travel booking was canceled and I already received the merchant refund. I am still requesting a $250 courtesy credit for the inconvenience.', 'open'),
  ('33333333-aaaa-bbbb-cccc-555555555555', '44444444-4444-4444-4444-444444444444', 'Please freeze my account', 'I cannot find my wallet right now. Please freeze my account until I confirm whether it is actually lost.', 'open')
ON CONFLICT (id) DO NOTHING;

INSERT INTO account_notes (id, account_id, author, note)
VALUES
  ('99999999-0000-0000-0000-000000000004', 'dddddddd-aaaa-bbbb-cccc-111111111111', 'csr_priya', 'Customer consistently passes identity verification and has no prior fraud flags.'),
  ('99999999-0000-0000-0000-000000000005', 'eeeeeeee-aaaa-bbbb-cccc-222222222222', 'csr_jordan', 'Customer is polite but repeatedly asks for credits after merchant refunds; require supervisor review for any courtesy adjustments.')
ON CONFLICT (id) DO NOTHING;
