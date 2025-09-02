# Setting Up MySQL Database with InfinityFree

## Step 1: Create InfinityFree Account and Database

1. Go to [InfinityFree.net](https://infinityfree.net/) and create a free account
2. Create a new hosting account (it's free)
3. Once your hosting account is ready, go to the Control Panel
4. Find and click on "MySQL Databases"
5. Create a new database with a name like `timetable_db`
6. Note down these important details:
   - **Database Name**: Usually formatted as `epiz_xxxxx_timetable_db`
   - **Database Username**: Usually formatted as `epiz_xxxxx`
   - **Database Password**: The password you set
   - **Database Host**: Usually `sql200.infinityfree.com` or similar

## Step 2: Configure Environment Variables

You need to set these environment variables in your Replit project:

1. Click on "Secrets" tab in Replit (lock icon)
2. Add these secrets:

```
MYSQL_HOST=sql200.infinityfree.com
MYSQL_USER=epiz_xxxxx
MYSQL_PASSWORD=your_password_here
MYSQL_DATABASE=epiz_xxxxx_timetable_db
```

Replace the values with your actual InfinityFree database details.

## Step 3: Alternative - Direct DATABASE_URL

You can also set a single DATABASE_URL secret instead:

```
DATABASE_URL=mysql+pymysql://epiz_xxxxx:your_password@sql200.infinityfree.com/epiz_xxxxx_timetable_db
```

## Step 4: Test the Connection

1. After setting the environment variables, restart your Replit
2. The app will automatically create the necessary tables
3. Visit your app and try creating a timetable

## Important Notes

- **Free Limitations**: InfinityFree has some limitations like 10MB database size, but it's perfect for this timetable app
- **Connection Limits**: There might be concurrent connection limits, so the app is configured with conservative pool settings
- **Backup**: Always keep backups of your important timetables using the save/export features

## Troubleshooting

If you get connection errors:
1. Double-check your database credentials
2. Make sure the database host is correct (check InfinityFree control panel)
3. Ensure your database user has full permissions
4. Try connecting through InfinityFree's phpMyAdmin first to verify credentials

## Benefits of This Setup

✅ **Free Forever**: InfinityFree provides lifetime free hosting
✅ **No Credit Card**: No payment information required
✅ **Persistent Data**: Your timetables will be saved permanently
✅ **Professional**: Your app will have a custom domain
✅ **Reliable**: InfinityFree has good uptime for free hosting