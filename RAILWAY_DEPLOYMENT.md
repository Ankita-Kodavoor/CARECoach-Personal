# Deploying to Railway

This guide explains how to deploy the CARE Coach app to Railway.

## Prerequisites

1. A Railway account (https://railway.app)
2. Your code pushed to a Git repository (GitHub, GitLab)
3. OpenAI API key

## Deployment Steps

### 1. Create a New Project in Railway

1. Log in to your Railway account
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Connect to your GitHub account if not already connected
5. Select the repository containing your CARE Coach code

### 2. Add a PostgreSQL Database

1. In your project dashboard, click "New Service"
2. Select "Database" from the dropdown
3. Choose "PostgreSQL"
4. Railway will automatically provision a PostgreSQL database
5. The `DATABASE_URL` environment variable will automatically be added to your project

### 3. Configure Environment Variables

1. In your project dashboard, click on your deployed service
2. Go to the "Variables" tab
3. Add the following environment variables:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `PORT`: 5000 (Railway will override this, but it's good to set)
   - Any other environment variables from `.env.example` you want to customize

### 4. Deploy

Railway should automatically deploy your application. If not:

1. Go to the "Deployments" tab
2. Click "Deploy Now"

### 5. Verify Deployment

1. Once deployment is complete, click on the URL Railway provides
2. Test that your application works correctly

## Troubleshooting

If your application doesn't work correctly:

1. Check the logs in the "Logs" tab
2. Verify that all environment variables are set correctly
3. Ensure your application is listening on the correct port

## Database Migrations

The application will automatically create the necessary tables when it first starts up. If you need to modify the database schema in the future, you can:

1. Update the schema in `postgres_schema.py`
2. Redeploy your application

## Custom Domain (Optional)

1. In your project settings, go to the "Settings" tab
2. Under "Domains", click "Generate Domain" or "Custom Domain"
3. Follow the instructions to set up your custom domain
