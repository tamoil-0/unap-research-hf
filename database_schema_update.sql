-- Schema update for items table
-- Add normalized text columns if they don't exist

-- Check and add title_norm column
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'items' AND column_name = 'title_norm'
    ) THEN
        ALTER TABLE items ADD COLUMN title_norm TEXT;
    END IF;
END $$;

-- Check and add abstract_norm column
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'items' AND column_name = 'abstract_norm'
    ) THEN
        ALTER TABLE items ADD COLUMN abstract_norm TEXT;
    END IF;
END $$;

-- Update existing records with normalized text
UPDATE items 
SET title_norm = LOWER(TRIM(title)),
    abstract_norm = LOWER(TRIM(abstract))
WHERE title_norm IS NULL OR abstract_norm IS NULL;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_items_title_norm ON items(title_norm);
CREATE INDEX IF NOT EXISTS idx_items_abstract_norm ON items USING gin(to_tsvector('english', abstract_norm));
