# Vercel Deployment Setup

## Database Setup Required

Vercel doesn't support SQLite. You need to add a PostgreSQL database:

1. Go to your Vercel project dashboard
2. Go to "Storage" tab
3. Create a new "Postgres" database
4. Copy the DATABASE_URL
5. Go to "Settings" > "Environment Variables"
6. Add: `DATABASE_URL` = (paste your postgres URL)
7. Redeploy the project

The app will automatically use PostgreSQL when DATABASE_URL is set.
