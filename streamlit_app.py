import requests
import random
import streamlit as st
import pandas as pd
import numpy as np
import base64
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
 
def get_spotify_access_token(client_id, client_secret):
    auth_url = 'https://accounts.spotify.com/api/token'
    auth_response = requests.post(auth_url, {
        'grant_type': 'client_credentials'
    }, headers={
        'Authorization': f'Basic {base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()}'
    })
    if auth_response.status_code == 200:
        return auth_response.json()['access_token']
    else:
        return None

# Fungsi untuk mengambil URL gambar album dari Spotify
def get_album_art(track_id, token):
    spotify_endpoint = f"https://api.spotify.com/v1/tracks/{track_id}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(spotify_endpoint, headers=headers)
    if response.status_code == 200:
        track_data = response.json()
        return track_data['album']['images'][0]['url']
    else:
        return None

# Ganti dengan Client ID dan Client Secret yang valid dari Spotify Developer Dashboard
CLIENT_ID = '8a056f31514c4db2a8b2048086f6e3ef'
CLIENT_SECRET = '0fcffe48f39e4440a4fb68c77d42d5bc'


# Fungsi untuk merekomendasikan lagu berdasarkan mood dan kelompok umur
def kategorikan_umur(umur):
    if umur < 5:
        return 'bayi'
    elif umur <= 9:
        return 'anak-anak'
    elif umur <= 19:
        return 'remaja'
    elif umur <= 59:
        return 'dewasa'
    else:
        return 'lansia'
    
def recommend_by_mood_and_age(mood, umur_pengguna, df, features, token):
    # Ubah umur menjadi kategori umur
    age_group = kategorikan_umur(umur_pengguna)
    # Ubah mood menjadi huruf kecil untuk mencocokkan dengan kolom DataFrame
    mood_column = mood.lower() 
    # Saring lagu berdasarkan kolom mood yang sesuai dan kelompok umur
    filtered_songs = df[(df[mood_column] == 1) & (df['umur'] == age_group)]
    
    # Jika DataFrame yang difilter tidak kosong, lanjutkan dengan proses
    if not filtered_songs.empty:

        # Inisialisasi StandardScaler untuk menormalkan fitur-fitur
        scaler = StandardScaler()

        # Fit dan transformasi fitur lagu dengan scaler
        song_features = scaler.fit_transform(filtered_songs[features])
        
        # Hitung matriks kemiripan kosinus antara lagu-lagu berdasarkan fiturnya
        similarity_matrix = cosine_similarity(song_features)
        
        # Pilih indeks acak dari lagu yang difilter sebagai lagu referensi
        reference_song_index = random.randint(0, len(filtered_songs) - 1)
        # Ambil skor kemiripan untuk lagu referensi tersebut
        song_similarity = similarity_matrix[reference_song_index]
        
        # Dapatkan indeks lagu dengan skor kemiripan tertinggi terhadap lagu referensi
        similar_songs_idx = np.argsort(-song_similarity)[:min(10, len(filtered_songs))]
        
        # Pilih lagu yang direkomendasikan berdasarkan indeks yang didapat
        recommended_songs = filtered_songs.iloc[similar_songs_idx][['track_name', 'track_id']].to_dict('records')
    
        # Mengambil gambar album untuk setiap lagu yang direkomendasikan
        for song in recommended_songs:
            song['image_url'] = get_album_art(song['track_id'], token)

        return recommended_songs
        # Simpan daftar lagu yang direkomendasikan ke file dengan format pickle
        with open('rekomendasi_mood_age.pkl', 'wb') as f:
            pickle.dump(recommended_songs, f)
            
        # Kembalikan daftar lagu yang direkomendasikan
        return recommended_songs
    else:
        # Jika DataFrame kosong, beri tahu tidak ada lagu yang cocok ditemukan
        return "Tidak ditemukan lagu dengan mood dan kelompok umur tersebut dalam dataset."

# Contoh fitur yang akan digunakan untuk menghitung kemiripan
features = ['danceability', 'acousticness', 'energy', 'instrumentalness', 'tempo', 'valence', 'speechiness']
 
file_path = "cluster.csv"  # Specify the path to your CSV file here
df = pd.read_csv(file_path)

st.title('Sistem Rekomendasi Musik Berdasarkan Suasana Hati dan Umur Pada Spotify Menggunakan Metode K-Means') 

# Ganti dengan number_input untuk input umur
umur_pengguna = st.number_input('Masukkan Umur', min_value=0, max_value=120, step=1)

mood = st.selectbox('Pilih Suasana Hati', ['calm', 'energic', 'sad', 'happy', 'angry'])

if st.button('Rekomendasikan'):
    # Permintaan access token baru dari Spotify API
    spotify_access_token = get_spotify_access_token(CLIENT_ID, CLIENT_SECRET)
    
    if spotify_access_token:
        recommendations = recommend_by_mood_and_age(mood, umur_pengguna, df, features, spotify_access_token)
        if isinstance(recommendations, list):
            st.write('Rekomendasi Lagu:')
            cols = st.columns(5)
            col_index = 0
            for idx, song in enumerate(recommendations):
                if idx % 5 == 0 and idx > 0:
                    cols = st.columns(5)
                    col_index = 0
                with cols[col_index]:
                    st.markdown(f"""
                    <div style='text-align: center; border: 2px solid black; margin-bottom: 20px; border-radius: 5px;'>
                        <a style='text-decoration: none; color: black;' href='https://open.spotify.com/track/{song['track_id']}' target='_blank'>
                            <img src='{song['image_url']}' style='width:100%; border-bottom: 1px solid #ccc;'/>
                            <p style='padding: 10px 0; margin: 0;'>{song['track_name']}</p>
                        </a>
                    </div>
                    """, unsafe_allow_html=True)
                    col_index = (col_index + 1) % 5
        else:
            st.error(recommendations)
    else:
        st.error("Gagal mendapatkan token akses dari Spotify.")
