async function searchSong(query) {
  const token = process.env.SPOTIFY_TOKEN;
  if (!token) {
    throw new Error("SPOTIFY_TOKEN environment variable is not set.");
  }
  const res = await fetch(
    "https://api.spotify.com/v1/search?q=" +
      encodeURIComponent(query) +
      "&type=track&limit=1",
    {
      headers: { Authorization: "Bearer " + token },
    }
  );

  const data = await res.json();
  const track = data.tracks.items[0];

  return {
    track: track,
    title: track.name,
    artist: track.artists[0].name,
    release_date: track.album.release_date,
  };
}

searchSong("ชาวนากับงูเห่า").then(console.log);
