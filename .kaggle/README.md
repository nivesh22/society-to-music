# Kaggle Credentials

Put your `kaggle.json` file in this folder. It will never be committed (gitignored).

## How to get it
1. Go to https://www.kaggle.com → click your profile picture → **Settings**
2. Scroll to **API** → click **"Create New Token"**
3. A `kaggle.json` file will download — move it here

## What it looks like inside
```json
{
  "username": "your_kaggle_username",
  "key": "your_kaggle_api_key"
}
```

Once it's here, run `make samples` to download the data.
