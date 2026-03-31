import { createBrowserClient } from '@supabase/ssr'

export const createClient = () =>
    createBrowserClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://nemrjlimrnrusodivtoa.supabase.co',
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_mzFR3EawYdrwGVOtWfYmzA_QaVdkj_H'
    )
