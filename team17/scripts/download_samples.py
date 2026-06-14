import os
import sys
import zipfile
import pandas as pd
from kaggle.api.kaggle_api_extended import KaggleApi


def download_and_save(full_data=False):
    print("Authenticating with Kaggle...")
    api = KaggleApi()
    api.authenticate()

    os.makedirs("data/01_raw", exist_ok=True)

    file_suffix = "_full" if full_data else "_sample"
    nrows = None if full_data else 5000

    # 1. Spotify Charts
    print(f"\nDownloading Spotify Charts ({'Full' if full_data else 'Sample'})...")
    api.dataset_download_files("dhruvildave/spotify-charts", path=".")
    charts_zip = "spotify-charts.zip"
    with zipfile.ZipFile(charts_zip, "r") as z:
        csv_files = [f for f in z.namelist() if f.endswith(".csv")]
        with z.open(csv_files[0]) as f:
            df = pd.read_csv(f, nrows=nrows)
    out_file = f"data/01_raw/charts{file_suffix}.parquet"
    df.to_parquet(out_file, index=False)
    print(f"Saved {len(df)} rows to {out_file}")
    os.remove(charts_zip)

    # 2. Audio Features
    print(f"\nDownloading Audio Features ({'Full' if full_data else 'Sample'})...")
    api.dataset_download_files("rodolfofigueroa/spotify-12m-songs", path=".")
    audio_zip = "spotify-12m-songs.zip"
    with zipfile.ZipFile(audio_zip, "r") as z:
        csv_files = [f for f in z.namelist() if f.endswith(".csv")]
        with z.open(csv_files[0]) as f:
            df = pd.read_csv(f, nrows=nrows)
    out_file = f"data/01_raw/audio_features{file_suffix}.parquet"
    df.to_parquet(out_file, index=False)
    print(f"Saved {len(df)} rows to {out_file}")
    os.remove(audio_zip)

    # 3. GDELT Daily Emotions
    print(f"\nDownloading GDELT Daily Emotions ({'Full' if full_data else 'Sample'})...")
    api.dataset_download_files("nivesh22/gdelt-daily-emotions", path=".")
    gdelt_zip = "gdelt-daily-emotions.zip"
    with zipfile.ZipFile(gdelt_zip, "r") as z:
        csv_files = [f for f in z.namelist() if f.endswith(".csv")]
        with z.open(csv_files[0]) as f:
            df = pd.read_csv(f, nrows=nrows)
    out_file = "data/01_raw/gdelt.csv"
    df.to_csv(out_file, index=False)
    print(f"Saved {len(df)} rows to {out_file}")
    os.remove(gdelt_zip)


if __name__ == "__main__":
    full_data = len(sys.argv) > 1 and sys.argv[1] == "--full"
    download_and_save(full_data)
