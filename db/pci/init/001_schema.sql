CREATE TABLE cards (
    id uuid PRIMARY KEY,
    account_id uuid NOT NULL,
    token text UNIQUE NOT NULL,
    card_number text UNIQUE NOT NULL,
    expiration_month integer NOT NULL CHECK (expiration_month BETWEEN 1 AND 12),
    expiration_year integer NOT NULL,
    cvv_hash text NOT NULL,
    status text NOT NULL CHECK (status IN ('ACTIVE', 'FROZEN', 'EXPIRED', 'LOST')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE authorization_log (
    id uuid PRIMARY KEY,
    card_id uuid NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    merchant text,
    amount numeric(12,2) NOT NULL,
    approved boolean NOT NULL,
    reason text,
    created_at timestamptz NOT NULL DEFAULT now()
);