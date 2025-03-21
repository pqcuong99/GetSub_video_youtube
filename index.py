from yt_dlp import YoutubeDL
import re
import os
import google.generativeai as genai
import sys
from colorama import init, Fore, Style

# Khởi tạo colorama
init()

# Cấu hình API key cho Google Generative AI
genai.configure(api_key="AIzaSyDCyskSi5HKiPoCM84ab6E7AxskmRPiHKc")

def get_video_id(url):
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

def parse_vtt_time_to_seconds(time_str):
    try:
        time_str = time_str.strip()
        parts = time_str.split(':')
        if len(parts) == 3:
            h, m, s = parts
        elif len(parts) == 2:
            h = 0
            m, s = parts
        else:
            return 0
        s_parts = s.split('.')
        if len(s_parts) != 2:
            return float(h) * 3600 + float(m) * 60 + float(s)
        s, ms = s_parts
        return float(h) * 3600 + float(m) * 60 + float(s) + float(ms) / 1000
    except (ValueError, IndexError) as e:
        print(f"Lỗi phân tích thời gian '{time_str}': {e}")
        return 0

def rewrite_subtitle_with_ai(text,language_code):
    try:
        prompt = f"""Dựa trên nội dung của đoạn văn sau: '{text}', hãy viết lại một đoạn văn khác dài hơn 40% nhưng vẫn giữ đầy đủ ý chính. Sử dụng văn phong lôi cuốn, huyền bí, kỳ bí để thúc đẩy sự tò mò của người xem, truyền đạt năng lượng mạnh mẽ, mạch lạc, dễ hiểu và đúng trọng tâm."""
        if language_code == "en":
            prompt = f"""Based on the content of the following paragraph: '{text}', rewrite another paragraph 40% longer but still keeping the main idea. Use an engaging, mysterious, and enigmatic style to stimulate the viewer's curiosity, convey strong energy, be coherent, easy to understand, and be on point."""
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Lỗi khi viết lại phụ đề với AI: {str(e)}")
        return text

def log(message, color=Fore.GREEN):
    sys.stdout.write(f"\r{color}{message}{Style.RESET_ALL}")
    sys.stdout.flush()

def process_subtitles(vtt_file, video_id, folder_path, video_info,language_code):
    with open(vtt_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    subtitle_blocks = {}
    all_sub_text = []
    current_time = 0
    current_text = []

    for line in lines:
        if '-->' in line:
            start_time = parse_vtt_time_to_seconds(line.split('-->')[0].strip())
            block_key = int(start_time // 60) * 60
            if block_key != current_time and current_text:
                subtitle_blocks[current_time] = ' '.join(current_text)
                all_sub_text.append(' '.join(current_text))
                current_text = []
            current_time = block_key
        elif line.strip() and not line.startswith('WEBVTT') and not line.startswith('Kind:') and not line.startswith('Language:'):
            clean_line = re.sub(r'<[^>]+>', '', line.strip())
            if clean_line:
                current_text.append(clean_line)

    if current_text:
        subtitle_blocks[current_time] = ' '.join(current_text)
        all_sub_text.append(' '.join(current_text))

    # Tạo file sub_intime.txt (phụ đề gốc theo thời gian)
    intime_file = os.path.join(folder_path, "sub_intime.txt")
    with open(intime_file, 'w', encoding='utf-8') as f:
        for start_time, text in sorted(subtitle_blocks.items()):
            f.write(f"{start_time} - {start_time+60}: {text}\n\n")
    print(f"Đã ghi phụ đề gốc theo thời gian vào: {intime_file}")

    # Tạo file sub_ai.txt (phụ đề AI viết lại theo thời gian) với log
    ai_file = os.path.join(folder_path, "sub_ai.txt")
    total_blocks = len(subtitle_blocks)
    with open(ai_file, 'w', encoding='utf-8') as f:
        for i, (start_time, text) in enumerate(sorted(subtitle_blocks.items()), 1):
            log(f"Đang xử lý AI rewrite: {i}/{total_blocks} (Thời gian: {start_time}-{start_time+60}s)", Fore.CYAN)
            rewritten_text = rewrite_subtitle_with_ai(text,language_code)
            f.write(f"{start_time} - {start_time+60}: {rewritten_text}\n\n")
    print(f"\nĐã ghi phụ đề AI viết lại vào: {ai_file}")

    # Tạo file sub_real.txt (nội dung phụ đề gốc, không mốc thời gian)
    real_file = os.path.join(folder_path, "sub_real.txt")
    with open(real_file, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(all_sub_text))
    print(f"Đã ghi nội dung phụ đề gốc vào: {real_file}")

    # Tạo file infor.txt (tiêu đề và mô tả video)
    infor_file = os.path.join(folder_path, "infor.txt")
    with open(infor_file, 'w', encoding='utf-8') as f:
        f.write(f"Title: \n{video_info.get('title', 'Không có tiêu đề')}\n\n")
        f.write(f"Description: \n{video_info.get('description', 'Không có mô tả')}\n")
    print(f"Đã ghi tiêu đề và mô tả video vào: {infor_file}")

def download_and_process_subtitles():
    video_url = input("Nhập link video YouTube: ")
    
    print("Chọn ngôn ngữ phụ đề:")
    print("1: Tiếng Việt (vi)")
    print("2: Tiếng Anh (en)")
    print("3: Ngôn ngữ khác (other)")
    
    lang_choice = input("Nhập số tương ứng (1/2/3): ")
    
    lang_map = {'1': 'vi', '2': 'en', '3': None}
    selected_lang = lang_map.get(lang_choice, None)
    
    video_id = get_video_id(video_url)
    if not video_id:
        print("Không thể lấy ID video từ URL!")
        return
    
    folder_name = f"subtitle_{video_id}"
    os.makedirs(folder_name, exist_ok=True)
    
    ydl_opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': [selected_lang] if selected_lang else ['all'],
        'skip_download': True,
        'outtmpl': os.path.join(folder_name, f'{video_id}.%(ext)s'),
        'subtitle_format': 'vtt',
        'get_title': True,  # Lấy tiêu đề
        'get_description': True,  # Lấy mô tả
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            print("Đang tải phụ đề và thông tin video...")
            info_dict = ydl.extract_info(video_url, download=False)  # Lấy thông tin mà không tải video
            ydl.download([video_url])  # Tải phụ đề
        
        for file in os.listdir(folder_name):
            if file.startswith(video_id) and file.endswith('.vtt'):
                vtt_file = os.path.join(folder_name, file)
                print(f"Đang xử lý: {vtt_file}")
                process_subtitles(vtt_file, video_id, folder_name, info_dict,selected_lang)
        
    except Exception as e:
        print(f"Có lỗi xảy ra: {str(e)}")

if __name__ == "__main__":
    download_and_process_subtitles()