import streamlit as st
import subprocess
import os
import time
import json
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# --- ΡΥΘΜΙΣΗ MOBILE UI ---
st.set_page_config(page_title="TikTok AI Suite", page_icon="🎬", layout="centered")

# CSS για Mobile-First εμπειρία και Safe Zone Overlay
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 480px; }
    .safe-zone-box {
        position: relative;
        width: 100%;
        border-radius: 16px;
        overflow: hidden;
        border: 2px solid #333;
    }
    .tiktok-ui-right {
        position: absolute; right: 8px; bottom: 80px;
        background: rgba(255, 0, 80, 0.35); border: 1px dashed #ff0050;
        color: white; font-size: 10px; padding: 6px 4px; border-radius: 8px;
        pointer-events: none; z-index: 10; text-align: center;
    }
    .tiktok-ui-bottom {
        position: absolute; left: 8px; right: 60px; bottom: 12px;
        background: rgba(0, 242, 234, 0.25); border: 1px dashed #00f2ea;
        color: white; font-size: 10px; padding: 6px; border-radius: 8px;
        pointer-events: none; z-index: 10;
    }
</style>
""", unsafe_allow_html=True)

# --- STRUCTURED OUTPUT SCHEMA ---
class AuditItem(BaseModel):
    timestamp: str = Field(description="Χρονικό σημείο π.χ. 0:03")
    category: str = Field(description="Hook, SafeZone, Retention, ή Guidelines")
    issue: str = Field(description="Τι πρόβλημα εντοπίστηκε")
    fix: str = Field(description="Συγκεκριμένη οδηγία διόρθωσης")

class TikTokStrategy(BaseModel):
    viral_score: int = Field(description="Βαθμολογία 0-100")
    hook_status: str = Field(description="Strong ή Weak")
    alternative_hooks: list[str] = Field(description="2 εναλλακτικά hooks στα Ελληνικά")
    best_clip_window: str = Field(description="Ποιο κομμάτι του YouTube βίντεο να κοπεί για TikTok π.χ. 0:15 - 1:05")
    audit_timeline: list[AuditItem]
    guidelines_risk: str = Field(description="Low, Medium, ή High + αιτιολόγηση για shadowban")
    seo_caption: str = Field(description="Έτοιμη περιγραφή με keywords")
    hashtags: list[str]

# --- ΛΕΙΤΟΥΡΓΙΑ ΚΑΤΕΒΑΣΜΑΤΟΣ ΑΠΟ YOUTUBE ---
def download_youtube_clip(url: str, output_path: str = "input_video.mp4"):
    if os.path.exists(output_path):
        os.remove(output_path)
    # Κατεβάζει έως 480p mp4 και κόβει τα πρώτα 90 δευτερόλεπτα για ταχύτητα
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]",
        "--download-sections", "*00:00:00-00:01:30",
        "--force-keyframes-at-cuts",
        "-o", output_path,
        url
    ]
    subprocess.run(cmd, check=True)
    return output_path

# --- ΑΝΑΛΥΣΗ ΜΕ GEMINI ---
def analyze_with_gemini(video_path: str, api_key: str) -> dict:
    client = genai.Client(api_key=api_key)
    
    uploaded_file = client.files.upload(file=video_path)
    while uploaded_file.state.name == "PROCESSING":
        time.sleep(2)
        uploaded_file = client.files.get(name=uploaded_file.name)

    prompt = """
    Είσαι Senior TikTok Strategist & Compliance Officer. 
    Ανάλυσε αυτό το βίντεο (που προέρχεται από YouTube) για να μετατραπεί σε viral TikTok (9:16).
    1. Εντόπισε ποιο χρονικό διάστημα έχει το δυνατότερο περιεχόμενο.
    2. Αξιολόγησε το Hook στα πρώτα 2 δευτερόλεπτα και δώσε 2 καλύτερες εναλλακτικές.
    3. Εντόπισε προβλήματα καδραρίσματος (αν κόβονται πρόσωπα/κείμενα σε 9:16 ή πέφτουν στα κουμπιά δεξιά/κάτω).
    4. Έλεγξε αυστηρά για TikTok Community Guidelines (λέξεις/εικόνες που ρίχνουν το reach).
    5. Φτιάξε SEO caption και hashtags.
    Απάντησε στα Ελληνικά.
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[uploaded_file, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TikTokStrategy,
            temperature=0.4
        )
    )
    
    client.files.delete(name=uploaded_file.name)
    return json.loads(response.text)

# --- INTERFACE ---
st.title("🎬 TikTok AI Content Suite")

api_key = st.secrets.get("GEMINI_API_KEY", "") or st.text_input("Gemini API Key", type="password")
yt_url = st.text_input("Επικόλλησε YouTube Link:", placeholder="https://www.youtube.com/watch?v=...")

if st.button("🚀 Ανάλυση & Μετατροπή Στρατηγικής", use_container_width=True):
    if not api_key or not yt_url:
        st.error("Συμπλήρωσε API Key και YouTube URL.")
    else:
        with st.status("Επεξεργασία βίντεο...", expanded=True) as status:
            try:
                st.write("📥 Λήψη & βελτιστοποίηση από YouTube...")
                video_file = download_youtube_clip(yt_url)
                
                st.write("🧠 Multimodal ανάλυση (Vision + Audio + Guidelines)...")
                data = analyze_with_gemini(video_file, api_key)
                status.update(label="Ολοκληρώθηκε!", state="complete", expanded=False)

                # --- ΑΠΟΤΕΛΕΣΜΑΤΑ ---
                col1, col2 = st.columns(2)
                col1.metric("Viral Score", f"{data['viral_score']}/100")
                col2.metric("Guidelines Risk", data['guidelines_risk'].split()[0])

                st.info(f"✂️ **Προτεινόμενο Απόσπασμα:** {data['best_clip_window']}")

                # Video Preview με Safe Zones
                st.subheader("📱 Προεπισκόπηση & Safe Zones")
                st.markdown('<div class="safe-zone-box">', unsafe_allow_html=True)
                st.video(video_file)
                st.markdown("""
                    <div class="tiktok-ui-right">❤️<br>💬<br>🔖<br>↪️<br>Buttons</div>
                    <div class="tiktok-ui-bottom">⚠️ Περιοχή Περιγραφής / Captions (Μην βάζεις κείμενο εδώ)</div>
                </div>
                """, unsafe_allow_html=True)

                # Hooks
                st.subheader("🪝 Εναλλακτικά Hooks")
                for i, hook in enumerate(data['alternative_hooks'], 1):
                    st.success(f"**Hook {i}:** {hook}")

                # Timeline Feedback
                st.subheader("⏱️ Διορθώσεις ανά Δευτερόλεπτο")
                for item in data['audit_timeline']:
                    with st.expander(f"{item['timestamp']} — [{item['category']}] {item['issue']}"):
                        st.write(f"**Λύση:** {item['fix']}")

                # SEO & Guidelines
                st.subheader("🔍 SEO & Ασφάλεια")
                st.text_area("Έτοιμο Caption:", f"{data['seo_caption']}\n\n{' '.join(data['hashtags'])}")
                st.warning(f"**Έλεγχος Κανονισμών:** {data['guidelines_risk']}")

            except Exception as e:
                st.error(f"Σφάλμα: {e}")