CREATE TABLE customers (
    id uuid PRIMARY KEY,
    first_name text NOT NULL,
    last_name text NOT NULL,
    email text UNIQUE NOT NULL,
    phone text,
    date_of_birth date,
    address text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE accounts (
    id uuid PRIMARY KEY,
    customer_id uuid NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    account_number text UNIQUE NOT NULL,
    account_type text NOT NULL CHECK (account_type IN ('checking', 'savings')),
    balance numeric(12,2) NOT NULL CHECK (balance >= 0),
    currency text NOT NULL DEFAULT 'USD',
    status text NOT NULL CHECK (status IN ('ACTIVE', 'FROZEN', 'CLOSED')),
    card_token text UNIQUE NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE transactions (
    id uuid PRIMARY KEY,
    account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    amount numeric(12,2) NOT NULL,
    currency text NOT NULL DEFAULT 'USD',
    transaction_type text NOT NULL CHECK (transaction_type IN ('purchase', 'refund', 'credit')),
    merchant_name text,
    description text,
    status text NOT NULL CHECK (status IN ('pending', 'approved', 'declined')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE support_tickets (
    id uuid PRIMARY KEY,
    customer_id uuid REFERENCES customers(id) ON DELETE SET NULL,
    subject text NOT NULL,
    body text NOT NULL,
    status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed', 'escalated', 'resolved')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE account_notes (
    id uuid PRIMARY KEY,
    account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    author text NOT NULL,
    note text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
    id uuid PRIMARY KEY,
    actor text NOT NULL,
    action text NOT NULL,
    resource text NOT NULL,
    before_state jsonb,
    after_state jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
