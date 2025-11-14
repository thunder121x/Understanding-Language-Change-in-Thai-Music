import pandas as pd
from playwright.sync_api import sync_playwright

df = pd.read_csv("thai_songs_all_years_final4พ-ฦ.csv")

# -----------------------------
# 1. Sample 50 rows
# -----------------------------
release_verify_df = df[['song_title', 'artist', 'release_year']].sample(
    n=50,
    random_state=42
).reset_index(drop=True)

# Add empty column for manual verification
release_verify_df["verified_year"] = None
print(release_verify_df.head())


# -----------------------------
# 2. Playwright search function
# -----------------------------
def google_search_song(title: str, artist: str):
    query = f"{title} {artist} เพลง ปี ออกปี"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        url = "https://www.google.com/search?q=" + query.replace(" ", "+")
        page.goto(url, timeout=60000)

        print("\n-----------------------------------------")
        print("Opened Google Search:")
        print(query)
        print("-----------------------------------------\n")

        # Wait for results
        page.wait_for_timeout(3000)

        # Keep browser open while user reads result
        input("Press ENTER after checking the year in browser... ")

        browser.close()


# -----------------------------
# 3. Loop through songs
# -----------------------------
for i, row in release_verify_df.iterrows():
    print(f"\n===== {i+1}/50 =====")
    print(f"Song:   {row['song_title']}")
    print(f"Artist: {row['artist']}")
    print(f"Original extracted year: {row['release_year']}")

    # open google
    google_search_song(row["song_title"], row["artist"])

    # Ask user to type verified year
    year = input("Enter VERIFIED release year (or press Enter to skip): ").strip()
    if year != "":
        release_verify_df.at[i, "verified_year"] = year
    else:
        release_verify_df.at[i, "verified_year"] = None

    print("Saved.")


# -----------------------------
# 4. Save the result (optional)
# -----------------------------
release_verify_df.to_csv("release_year_manual_verify.csv", index=False)
print("\nSaved verification file: release_year_manual_verify.csv")