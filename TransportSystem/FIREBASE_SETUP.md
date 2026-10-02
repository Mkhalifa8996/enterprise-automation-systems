# Firebase Cloud Sync Setup

The application **contains no Firebase data**. Every user enters their own
project details, and those credentials are never shared with anyone.

## Where are your credentials stored?

On first launch a **"Firebase sync setup"** window appears. What you enter is
saved to `firebase_sync_config.json` **next to the program on your own
machine**, and that file is excluded from Git.

To erase them permanently: delete the file and restart the program.

---

## Step 1: Create your own Firebase project

1. Open the [Firebase Console](https://console.firebase.google.com) and create
   a new project.
2. Under **Build → Realtime Database**, create a database.
3. Copy the **database URL** — it looks like this:

   ```
   https://MY-PROJECT-default-rtdb.europe-west1.firebasedatabase.app
   ```

## Step 2: Enable a sign-in method

Under **Build → Authentication → Sign-in method**, enable one of:

- **Email/Password** — simplest, and the default in the setup window.
- **Phone** — available from the "Sign in with phone number" button in the
  same window.

If you choose Email/Password, add a user under **Authentication → Users**.

## Step 3: Copy your Web API Key

From **Project settings (⚙) → General → Your apps → Web API Key**, copy the key.

## Step 4: Set the database rules

In **Realtime Database → Rules**, paste:

```json
{
  "rules": {
    "transport_sync": {
      ".read": "auth != null",
      ".write": "auth != null"
    }
  }
}
```

> Without these rules, sync fails with a `Permission denied` error.

## Step 5: Enter your details in the application

Press **Save and sync** after filling in:

| Field | Value |
|---|---|
| Firebase Realtime Database URL | The URL copied in step 1 |
| Web API Key | The key copied in step 3 |
| Email address | The Firebase user you created |
| Firebase password | That user's password |

These are stored locally and reused on every subsequent run.

---

## Alternative: configure through a `.env` file

Copy `.env.example` to `.env` and fill in:

```
FIREBASE_API_KEY=...
FIREBASE_EMAIL=...
FIREBASE_PASSWORD=...
FIREBASE_DATABASE_URL=https://MY-PROJECT-default-rtdb.europe-west1.firebasedatabase.app
```

The `.env` file is read automatically at startup.

---

## Common errors

| Error | Cause |
|---|---|
| `Permission denied` | Database rules are not set (see step 4) |
| `400 Invalid API key` | The Web API Key is wrong, or copied from the wrong screen |
| `EMAIL_NOT_FOUND` | The user does not exist under Authentication → Users |
| `INVALID_LOGIN_CREDENTIALS` | Email or password is incorrect |
| Connection failed | The database URL is incomplete, or does not end in `firebasedatabase.app` |