-- The "Duplicate": Master list of billable properties
CREATE TABLE tax_duplicate (
    parcel_id TEXT PRIMARY KEY,
    owner_name TEXT,
    property_address TEXT,
    mailing_address TEXT,
    bill_number TEXT,
    assessment_value REAL,
    homestead_exclusion REAL DEFAULT 0.0, -- Assessment reduction (Act 50/1)
    farmstead_exclusion REAL DEFAULT 0.0, -- Assessment reduction (Act 50/1)
    face_tax_amount REAL, -- Should be calculated on (Assessment - Exclusions)
    discount_amount REAL,
    penalty_amount REAL,
    tax_type TEXT, -- 'Real Estate', 'Per Capita', 'Fire'
    bill_issue_date TEXT DEFAULT '2025-03-01', -- CRITICAL: Anchors the Discount/Face/Penalty periods (supports Interims)
    is_installment_plan BOOLEAN DEFAULT 0, -- Tracks if using installment payments
    is_interim BOOLEAN DEFAULT 0, -- Tracks interim bills (new construction)
    status TEXT DEFAULT 'UNPAID' -- 'UNPAID', 'PARTIAL', 'PAID', 'RETURNED', 'EXONERATED'
);

-- The "Journal": Every check, cash exchange, or non-cash adjustment
CREATE TABLE transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_received TEXT, -- Physical receipt date
    postmark_date TEXT, -- CRITICAL: Legal date for determining Discount/Face/Penalty
    parcel_id TEXT,
    transaction_type TEXT, -- 'PAYMENT', 'EXONERATION', 'RETURN', 'NSF_REVERSAL'
    payment_method TEXT, -- 'CHECK', 'CASH', 'MONEY_ORDER', 'NONE' (for returns/exonerations)
    check_number TEXT,
    amount_paid REAL, -- Amount of money actually received (Negative for Reversals)
    balance_remaining REAL, -- For tracking partial payments
    payment_period TEXT, -- 'DISCOUNT', 'FACE', 'PENALTY'
    installment_number INTEGER, -- 1, 2, or 3
    deposit_batch_id INTEGER, -- Links to a specific bank run
    is_closed BOOLEAN DEFAULT 0, -- If 1, this transaction is LOCKED
    image_path TEXT, -- Path to stored image of check
    notes TEXT,
    FOREIGN KEY(parcel_id) REFERENCES tax_duplicate(parcel_id)
);

-- The "Remittance": Money leaving account to Township/County
CREATE TABLE remittances (
    remittance_id INTEGER PRIMARY KEY,
    date_sent TEXT,
    recipient TEXT, -- 'Township', 'County', 'School Dist'
    amount REAL,
    check_number_from_you TEXT,
    period_covered TEXT
);

-- The "Log": Immutable audit trail (System Events)
CREATE TABLE system_log (
    timestamp TEXT,
    action TEXT, -- 'Import', 'Update', 'Delete'
    details TEXT
);

-- The "Change Log": Detailed Data Auditing (Value Changes)
CREATE TABLE change_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    table_name TEXT,
    record_id TEXT, -- Primary Key of affected row
    field_name TEXT,
    old_value TEXT,
    new_value TEXT,
    action_type TEXT, -- 'INSERT', 'UPDATE', 'DELETE'
    user_context TEXT DEFAULT 'CLI'
);
