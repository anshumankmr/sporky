import './PlaylistCard.css';

export default function PlaylistCard({ tracks }) {
  if (!tracks || tracks.length === 0) return null;

  return (
    <div className="playlist-card">
      <div className="playlist-card__header">
        <span className="playlist-card__count">{tracks.length} tracks</span>
      </div>
      <ul className="playlist-card__list">
        {tracks.map((track, i) => {
          const year = track.release_date ? track.release_date.slice(0, 4) : null;
          return (
            <li key={track.uri || i} className="playlist-card__track">
              <span className="playlist-card__num">{i + 1}</span>
              <div className="playlist-card__info">
                <span className="playlist-card__name">{track.name}</span>
                <span className="playlist-card__meta">
                  {track.artist}
                  {track.album ? ` · ${track.album}` : ''}
                  {year ? ` · ${year}` : ''}
                </span>
              </div>
              {track.external_url && (
                <a
                  href={track.external_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="playlist-card__link"
                  title="Open in Spotify"
                >
                  ↗
                </a>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
