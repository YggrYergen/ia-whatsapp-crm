ALTER TABLE IF EXISTS test_feedback ENABLE ROW LEVEL SECURITY;
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'test_feedback' AND policyname = 'Allow insert test_feedback') THEN
        CREATE POLICY "Allow insert test_feedback" ON test_feedback FOR INSERT WITH CHECK (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'test_feedback' AND policyname = 'Allow select test_feedback') THEN
        CREATE POLICY "Allow select test_feedback" ON test_feedback FOR SELECT USING (true);
    END IF;
END $$;
