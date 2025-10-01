-- Database Migration: Move Supplier_Depot_FK to od_pair table
-- This script safely migrates the Supplier_Depot_FK column from delivery_options and collection_options to od_pair
-- while preserving all existing relationships

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- Step 1: Add Supplier_Depot_FK column to od_pair table
ALTER TABLE od_pair ADD COLUMN Supplier_Depot_FK INTEGER;

-- Step 2: Update od_pair with Supplier_Depot_FK from delivery_options
-- Use DEL_Valid_FK to join with delivery_options.DEL_Valid_PK
UPDATE od_pair 
SET Supplier_Depot_FK = (
    SELECT do.Supplier_Depot_FK 
    FROM delivery_options do 
    WHERE od_pair.DEL_Valid_FK = do.DEL_Valid_PK
)
WHERE DEL_Valid_FK IS NOT NULL;

-- Step 3: Update od_pair with Supplier_Depot_FK from collection_options
-- Use COC_Valid_FK to join with collection_options.COC_Valid_PK
-- Only update if Supplier_Depot_FK is still NULL (prioritize DEL over COC if both exist)
UPDATE od_pair 
SET Supplier_Depot_FK = (
    SELECT co.Supplier_Depot_FK 
    FROM collection_options co 
    WHERE od_pair.COC_Valid_FK = co.COC_Valid_PK
)
WHERE COC_Valid_FK IS NOT NULL 
AND Supplier_Depot_FK IS NULL;

-- Step 4: Handle cases where both DEL and COC exist for same customer depot
-- Update remaining cases where COC exists but DEL took priority
UPDATE od_pair 
SET Supplier_Depot_FK = (
    SELECT co.Supplier_Depot_FK 
    FROM collection_options co 
    WHERE od_pair.COC_Valid_FK = co.COC_Valid_PK
)
WHERE COC_Valid_FK IS NOT NULL 
AND Supplier_Depot_FK != (
    SELECT co.Supplier_Depot_FK 
    FROM collection_options co 
    WHERE od_pair.COC_Valid_FK = co.COC_Valid_PK
)
AND EXISTS (
    SELECT 1 FROM collection_options co 
    WHERE od_pair.COC_Valid_FK = co.COC_Valid_PK
);

-- Validation queries (run these after migration to verify data integrity)
-- These are comments for manual verification:

-- Verify delivery_options relationships preserved:
-- SELECT COUNT(*) FROM od_pair od 
-- JOIN delivery_options do ON od.DEL_Valid_FK = do.DEL_Valid_PK 
-- WHERE od.Supplier_Depot_FK = do.Supplier_Depot_FK;

-- Verify collection_options relationships preserved:
-- SELECT COUNT(*) FROM od_pair od 
-- JOIN collection_options co ON od.COC_Valid_FK = co.COC_Valid_PK 
-- WHERE od.Supplier_Depot_FK = co.Supplier_Depot_FK;

-- Check for any NULL Supplier_Depot_FK where options exist:
-- SELECT COUNT(*) FROM od_pair 
-- WHERE (DEL_Valid_FK IS NOT NULL OR COC_Valid_FK IS NOT NULL) 
-- AND Supplier_Depot_FK IS NULL;

COMMIT;

-- Step 5: After manual verification, we can drop the old columns
-- (This will be done in a separate step after validation)
-- ALTER TABLE delivery_options DROP COLUMN Supplier_Depot_FK;
-- ALTER TABLE collection_options DROP COLUMN Supplier_Depot_FK;