import React from 'react';

function SignInPage() {
    // Replace these values with your app's Client ID and Redirect URI
    const clientId = '383112c27a96499a84786a7c40c24e35';
    const redirectUri = 'http://localhost:5173/signup'; // Ensure this matches the redirect URI set in your Spotify Developer Dashboard
    
    // Define the desired scopes (permissions)
    const scopes = [
        'user-read-private',
        'user-read-email'
    ];

    // Spotify authorization endpoint
    const authEndpoint = 'https://accounts.spotify.com/authorize';

    // Construct the authorization URL and redirect the user
    const handleSignIn = () => {
        const authUrl = `${authEndpoint}?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&scope=${encodeURIComponent(scopes.join(' '))}&response_type=token&show_dialog=true`;
        window.location.href = authUrl;
    };

    return (
        <div className="signin-container">
            <h2>Sign in with Spotify</h2>
            <button onClick={handleSignIn}>
                Sign In
            </button>
        </div>
    );
}

export default SignInPage;
