import os
import numpy as np
from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip, 
    ImageClip, ColorClip, TextClip
)
from PIL import Image, ImageFilter
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import subprocess
import sys

class ProgressManager:
    def __init__(self):
        self.console = Console()

    def print_message(self, message, style="bold green"):
        """In thông báo"""
        self.console.print(Panel(Text(message, style=style), border_style="blue"))

    def print_error(self, message):
        """In thông báo lỗi"""
        self.console.print(Panel(Text(message, style="bold red"), border_style="red"))

    def print_warning(self, message):
        """In thông báo cảnh báo"""
        self.console.print(Panel(Text(message, style="bold yellow"), border_style="yellow"))

class VideoProcessor:
    def __init__(self, config):
        self.config = config
        self.image_dir = config["video"].get("image_dir", "images")
        self.output_file = config["video"].get("output_file", "output_video.mp4")
        self.width = config["video"].getint("width", 1920)
        self.height = config["video"].getint("height", 1080)
        self.image_duration = config["video"].getfloat("image_duration", 6)
        self.fps = config["video"].getint("fps", 30)
        self.bitrate = config["video"].get("bitrate", "8000k")
        self.max_threads = config["video"].getint("max_threads", 10)
        
        # Image settings
        self.blur_radius = config["image"].getint("blur_radius", 10)
        self.overlay_opacity = config["image"].getint("overlay_opacity", 166)
        self.image_scale = config["image"].getfloat("scale", 0.9)
        
        # Logo settings
        self.logo_path = config["image"].get("logo_path", "")
        self.logo_width = config["image"].getint("logo_width", 250)
        self.logo_height = config["image"].getint("logo_height", 250)
        self.logo_margin_left = config["image"].getint("logo_margin_left", 50)
        self.logo_margin_top = config["image"].getint("logo_margin_top", 50)
        
        self.progress = ProgressManager()
        self.temp_files = []  # Danh sách các file tạm cần xóa

    def create_base_images(self, image_path):
        """Tạo ảnh nền và ảnh chính"""
        try:
            # Đọc ảnh gốc
            self.progress.print_message(f"Đang đọc ảnh: {os.path.basename(image_path)}")
            img = Image.open(image_path)
            if img is None:
                raise Exception("Không thể đọc ảnh")
                
            # Chuyển sang RGB nếu cần
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Tạo background - fit vào kích thước video
            background = img.copy()
            # Tính tỷ lệ để fit vào kích thước video
            ratio = max(self.width / background.size[0], self.height / background.size[1])
            new_size = (int(background.size[0] * ratio), int(background.size[1] * ratio))
            background = background.resize(new_size, Image.Resampling.LANCZOS)
            
            # Crop background để fit vào kích thước video
            start_x = (background.size[0] - self.width) // 2
            start_y = (background.size[1] - self.height) // 2
            background = background.crop(
                (start_x, start_y, start_x + self.width, start_y + self.height)
            )
            
            # Làm mờ background
            background = background.filter(ImageFilter.GaussianBlur(radius=self.blur_radius))
            
            # Tạo overlay
            overlay = Image.new('RGB', (self.width, self.height), 'white')
            overlay.putalpha(self.overlay_opacity)
            
            # Blend background với overlay
            background = background.convert('RGBA')
            overlay = overlay.convert('RGBA')
            background = Image.blend(background, overlay, 0.4)
            background = background.convert('RGB')
            
            # Xử lý ảnh chính - giữ tỷ lệ khung hình gốc
            main_img = img.copy()
            
            # Tính kích thước tối đa cho phép (70% của kích thước video)
            max_width = int(self.width * 0.7)
            max_height = int(self.height * 0.7)
            
            # Tính tỷ lệ scale để ảnh vừa với kích thước cho phép
            width_scale = max_width / main_img.size[0]
            height_scale = max_height / main_img.size[1]
            
            # Sử dụng tỷ lệ nhỏ hơn để đảm bảo ảnh không bị tràn
            scale = min(width_scale, height_scale)
            
            # Tính kích thước mới
            new_width = int(main_img.size[0] * scale)
            new_height = int(main_img.size[1] * scale)
            
            print(f"Original size: {main_img.size}")
            print(f"New size: {new_width}x{new_height}")
            
            # Resize ảnh với kích thước mới
            main_img = main_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Tạo ảnh cuối cùng
            final_img = background.copy()
            x_offset = (self.width - new_width) // 2
            y_offset = (self.height - new_height) // 2
            
            # Tạo mask cho main_img nếu cần
            if main_img.mode == 'RGBA':
                mask = main_img.split()[3]
            else:
                mask = None
                
            final_img.paste(main_img, (x_offset, y_offset), mask)
            
            # Thêm logo nếu có
            if self.logo_path and os.path.exists(self.logo_path):
                try:
                    logo = Image.open(self.logo_path)
                    if logo.mode != 'RGBA':
                        logo = logo.convert('RGBA')
                    logo = logo.resize((self.logo_width, self.logo_height), Image.Resampling.LANCZOS)
                    final_img.paste(logo, (self.logo_margin_left, self.logo_margin_top), logo)
                except Exception as e:
                    self.progress.print_warning(f"Lỗi khi thêm logo: {str(e)}")
            
            # Chuyển sang numpy array
            final_array = np.array(final_img)
            if final_array is None or final_array.size == 0:
                raise Exception("Không thể chuyển ảnh sang numpy array")
                
            return final_array
            
        except Exception as e:
            self.progress.print_error(f"Lỗi trong create_base_images: {str(e)}")
            # Trả về ảnh đen nếu có lỗi
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)

    def create_subtitle_clip(self, text, duration, start_time=0):
        """Tạo clip subtitle"""
        try:
            # Lấy cấu hình từ file config
            sub_config = self.config["subtitle"]
            # Lấy thông số subtitle từ config
            font = sub_config.get("font", "Arial")
            font_size = sub_config.getint("font_size", 70)
            color = sub_config.get("color", "#FFFFFF")
            stroke_color = sub_config.get("stroke_color", "#000000")
            stroke_width = sub_config.getint("stroke_width", 2)
            background_opacity = sub_config.getfloat("background_opacity", 0.7)
            padding = self.config['subtitle'].getint('background_padding', 15)
            
            # Tính toán kích thước tối đa cho subtitle (70% chiều rộng video)
            max_width = int(self.width * 0.7)
            
            # Tạo text clip với wrap
            txt_clip = TextClip(
                text,
                fontsize=font_size,
                font=font,
                color=color,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                method='label',
                align='center',
                size=(max_width, None),  # Giới hạn chiều rộng, tự động tính chiều cao
                interline=-1  # Giảm khoảng cách giữa các dòng
            )
            
            # Thêm background nếu cần
            if background_opacity > 0:
                # Tạo background clip
                bg_color = self.config['subtitle'].get('background_color', 'rgb(255,236,67)')
                # Chuyển đổi chuỗi rgb thành tuple
                if bg_color.startswith('rgb('):
                    bg_color = bg_color.replace('rgb(', '').replace(')', '')
                    r, g, b = map(int, bg_color.split(','))
                    bg_color = (r, g, b)
                
                # Tính kích thước background với padding
                bg_width = txt_clip.size[0] + (padding * 2)
                bg_height = txt_clip.size[1] + (padding * 2)
                
                # Tạo background đơn giản
                bg_clip = ColorClip(size=(bg_width, bg_height), color=bg_color)
                bg_clip = bg_clip.set_opacity(background_opacity)
                
                # Đặt text vào giữa background
                txt_clip = txt_clip.set_position(('center', 'center'))
                
                # Kết hợp background và text
                txt_clip = CompositeVideoClip([bg_clip, txt_clip])
            
            # Đặt vị trí
            position = sub_config.get("position", "bottom")
            if position == "bottom":
                margin_bottom = sub_config.getint("margin_bottom", 50)
                txt_clip = txt_clip.set_position(('center', f'bottom-{margin_bottom}'))
            elif position == "top":
                txt_clip = txt_clip.set_position(('center', 'top'))
            elif position == "center":
                txt_clip = txt_clip.set_position('center')
            else:  # custom
                x_pos = sub_config.getint("x_position", 0)
                y_pos = sub_config.getint("y_position", 0)
                txt_clip = txt_clip.set_position((x_pos, y_pos))
            
            # Đặt thời gian
            txt_clip = txt_clip.set_duration(duration).set_start(start_time)
            
            return txt_clip
            
        except Exception as e:
            self.progress.print_warning(f"Lỗi khi tạo subtitle clip: {str(e)}")
            return None

    def process_image(self, img_file, index, temp_dir, subtitles=None):
        """Xử lý một ảnh và tạo video clip"""
        try:
            # Tạo đường dẫn đầy đủ cho ảnh
            img_path = os.path.join(self.image_dir, img_file)
            if not os.path.exists(img_path):
                raise FileNotFoundError(f"Không tìm thấy file ảnh: {img_path}")
                
            # Đọc ảnh gốc
            self.progress.print_message(f"Đang xử lý ảnh: {img_file}")
            img = Image.open(img_path)
            if img is None:
                raise Exception("Không thể đọc ảnh")
                
            # Chuyển sang RGB nếu cần
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Tạo background - fit vào kích thước video 16:9
            background = img.copy()
            # Tính tỷ lệ để fit vào kích thước video
            ratio = max(self.width / background.size[0], self.height / background.size[1])
            new_size = (int(background.size[0] * ratio), int(background.size[1] * ratio))
            background = background.resize(new_size, Image.Resampling.LANCZOS)
            
            # Crop background để fit vào kích thước video
            start_x = (background.size[0] - self.width) // 2
            start_y = (background.size[1] - self.height) // 2
            background = background.crop(
                (start_x, start_y, start_x + self.width, start_y + self.height)
            )
            
            # Làm mờ background
            background = background.filter(ImageFilter.GaussianBlur(radius=self.blur_radius))
            
            # Tạo overlay
            overlay = Image.new('RGB', (self.width, self.height), 'white')
            overlay.putalpha(self.overlay_opacity)
            
            # Blend background với overlay
            background = background.convert('RGBA')
            overlay = overlay.convert('RGBA')
            background = Image.blend(background, overlay, 0.5)
            background = background.convert('RGB')
            
            # Xử lý ảnh chính - giữ tỷ lệ khung hình gốc
            main_img = img.copy()
            
            # Tính kích thước tối đa cho phép (90% của kích thước video)
            max_width = int(self.width * 0.9)
            max_height = int(self.height * 0.9)
            
            # Tính tỷ lệ scale để ảnh vừa với kích thước cho phép
            width_scale = max_width / main_img.size[0]
            height_scale = max_height / main_img.size[1]
            
            # Sử dụng tỷ lệ nhỏ hơn để đảm bảo ảnh không bị tràn và giữ nguyên tỷ lệ
            scale = min(width_scale, height_scale)
            
            # Tính kích thước mới
            new_width = int(main_img.size[0] * scale)
            new_height = int(main_img.size[1] * scale)
            
            # Resize ảnh với kích thước mới
            main_img = main_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Tạo video clip từ background
            clip = ImageClip(np.array(background))
            if clip is None:
                raise Exception(f"Không thể tạo clip từ background")
            
            # Đặt thời gian cho clip
            clip = clip.set_duration(self.image_duration)
            
            # Thêm hiệu ứng zoom cho ảnh chính
            def make_frame(t):
                try:
                    # Tạo ảnh mới với background
                    new_img = background.copy()
                    
                    # Tính tỷ lệ zoom (từ 75% đến 90%)
                    zoom_start = self.config["video"].getfloat("zoom_start", 0.9)
                    zoom_end = self.config["video"].getfloat("zoom_end", 1.4)
                    zoom_value = zoom_end - zoom_start
                    zoom_factor = zoom_start + (zoom_value * t / self.image_duration)
                    
                    # Tính kích thước mới cho ảnh chính với zoom
                    current_width = int(new_width * zoom_factor)
                    current_height = int(new_height * zoom_factor)
                    
                    # Resize ảnh chính với zoom
                    current_main_img = main_img.resize((current_width, current_height), Image.Resampling.LANCZOS)
                    
                    # Đặt ảnh chính vào giữa
                    x_offset = (self.width - current_width) // 2
                    y_offset = (self.height - current_height) // 2
                    
                    # Tạo mask cho main_img nếu cần
                    if current_main_img.mode == 'RGBA':
                        mask = current_main_img.split()[3]
                    else:
                        mask = None
                        
                    new_img.paste(current_main_img, (x_offset, y_offset), mask)
                    
                    # Thêm logo nếu có
                    if self.logo_path and os.path.exists(self.logo_path):
                        try:
                            logo = Image.open(self.logo_path)
                            if logo.mode != 'RGBA':
                                logo = logo.convert('RGBA')
                            logo = logo.resize((self.logo_width, self.logo_height), Image.Resampling.LANCZOS)
                            new_img.paste(logo, (self.logo_margin_left, self.logo_margin_top), logo)
                        except Exception as e:
                            self.progress.print_warning(f"Lỗi khi thêm logo: {str(e)}")
                    
                    return np.array(new_img)
                except Exception as e:
                    self.progress.print_warning(f"Lỗi trong make_frame: {str(e)}")
                    return np.array(background)
            
            # Áp dụng hiệu ứng zoom
            clip = clip.fl(lambda gf, t: make_frame(t))
            
            # Thêm subtitle nếu có
            if subtitles:
                current_subtitles = [sub for sub in subtitles 
                                  if sub["start"] <= index * self.image_duration < sub["end"]]
                for sub in current_subtitles:
                    try:
                        subtitle_clip = self.create_subtitle_clip(
                            sub["text"], 
                            sub["end"] - sub["start"],
                            sub["start"] - index * self.image_duration
                        )
                        if subtitle_clip is not None:
                            clip = CompositeVideoClip([clip, subtitle_clip])
                    except Exception as e:
                        self.progress.print_warning(f"Lỗi khi tạo subtitle clip: {str(e)}")
            
            # Lưu clip tạm
            output_path = os.path.join(temp_dir, f"temp_video_{index}.mp4")
            self.progress.print_message(f"Đang ghi clip tạm: {output_path}")
            
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Ghi clip ra file
            clip.write_videofile(
                output_path,
                fps=self.fps,
                codec="libx264",
                audio_codec="aac",
                preset="ultrafast",
                bitrate=self.bitrate,
                threads=1,
                verbose=False,
                logger=None
            )
            
            # Đóng clip
            clip.close()
            
            # Kiểm tra file đã được tạo
            if not os.path.exists(output_path):
                raise Exception(f"Không thể tạo file clip: {output_path}")
                
            if os.path.getsize(output_path) == 0:
                raise Exception(f"File clip rỗng: {output_path}")
                
            self.progress.print_message(f"Đã tạo clip thành công: {output_path}")
            return output_path
            
        except Exception as e:
            self.progress.print_error(f"Lỗi khi xử lý ảnh {img_file}: {str(e)}")
            return None

    def cleanup_temp_files(self):
        """Xóa các file tạm sau khi video đã được ghi thành công"""
        try:
            for path in self.temp_files:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                        self.progress.print_message(f"Đã xóa file tạm: {path}")
                    except Exception as e:
                        self.progress.print_warning(f"Không thể xóa file tạm {path}: {str(e)}")
            self.temp_files = []
        except Exception as e:
            self.progress.print_warning(f"Lỗi khi xóa file tạm: {str(e)}")

    def create_temp_subtitle_file(self, subtitles, output_dir):
        """Tạo file subtitle tạm thời"""
        try:
            # Tạo thư mục temp nếu chưa tồn tại
            temp_dir = os.path.abspath(os.path.join(output_dir, "temp"))
            os.makedirs(temp_dir, exist_ok=True)
            
            # Tạo file subtitle tạm
            subtitle_path = os.path.join(temp_dir, "temp_subtitle.ass")
            self.progress.print_message(f"Đang tạo file subtitle tạm: {subtitle_path}")
            
            # Lấy cấu hình subtitle
            font = self.config['subtitle'].get('font', 'Arial')
            font_size = self.config['subtitle'].getint('font_size', 44)
            color = self.config['subtitle'].get('color', '#FFFFFF')
            stroke_color = self.config['subtitle'].get('stroke_color', '#000000')
            stroke_width = self.config['subtitle'].getint('stroke_width', 0)
            position = self.config['subtitle'].get('position', 'bottom')
            margin_bottom = self.config['subtitle'].getint('margin_bottom', 50)
            
            # Ghi header ASS
            with open(subtitle_path, "w", encoding="utf-8") as f:
                f.write("[Script Info]\n")
                f.write("ScriptType: v4.00+\n")
                f.write("PlayResX: 1920\n")
                f.write("PlayResY: 1080\n")
                f.write("\n")
                f.write("[V4+ Styles]\n")
                f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
                f.write(f"Style: Default,{font},{font_size},&H{color},&H{color},&H{stroke_color},&H000000,0,0,0,0,100,100,0,0,1,{stroke_width},0,2,10,10,{margin_bottom},1\n")
                f.write("\n")
                f.write("[Events]\n")
                f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
                
                # Ghi các dòng subtitle
                for i, sub in enumerate(subtitles, 1):
                    start_time = self.format_time(sub["start"])
                    end_time = self.format_time(sub["end"])
                    f.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{sub['text']}\n")
            
            return subtitle_path
            
        except Exception as e:
            self.progress.print_error(f"Lỗi khi tạo file subtitle tạm: {str(e)}")
            return None

    def format_time(self, seconds):
        """Chuyển đổi thời gian từ giây sang định dạng ASS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        return f"{hours}:{minutes:02d}:{seconds:05.2f}"

    def create_subtitle_video(self, video_clip, subtitles, output_dir):
        """Tạo video chỉ chứa subtitle"""
        try:
            
            # Tạo thư mục temp nếu chưa tồn tại
            temp_dir = os.path.abspath(os.path.join(output_dir, "temp"))
            os.makedirs(temp_dir, exist_ok=True)
            
            # Tính tổng thời gian video
            total_duration = 0
            if subtitles:
                total_duration = max(sub["end"] for sub in subtitles)
            
            # Tạo video clip màu đen với cùng kích thước
            black_clip = ColorClip(size=(self.width, self.height), color=(0, 0, 0))
            black_clip = black_clip.set_duration(total_duration)
            
            # Tạo các subtitle clip
            subtitle_clips = []
            for sub in subtitles:
                try:
                    # Lấy cấu hình từ file config
                    sub_config = self.config["subtitle"]
                    
                    # Lấy thông số subtitle từ config
                    font = sub_config.get("font", "Arial")
                    font_size = sub_config.getint("font_size", 70)
                    color = sub_config.get("color", "#FFFFFF")
                    stroke_color = sub_config.get("stroke_color", "#000000")
                    stroke_width = sub_config.getint("stroke_width", 2)
                    position = sub_config.get("position", "bottom")
                    margin_bottom = sub_config.getint("margin_bottom", 50)
                    background_opacity = sub_config.getfloat("background_opacity", 0.7)
                    
                    # Tạo text clip
                    txt_clip = TextClip(
                        sub['text'],
                        fontsize=font_size,
                        font=font,
                        color=color,
                        stroke_color=stroke_color,
                        stroke_width=stroke_width,
                        method='label',
                        align='center'
                    )
                    
                    # Tạo background nếu cần
                    if background_opacity > 0:
                        # Tạo background clip
                        bg_color = self.config['subtitle'].get('background_color', 'rgb(255,236,67)')
                        # Chuyển đổi chuỗi rgb thành tuple
                        if bg_color.startswith('rgb('):
                            bg_color = bg_color.replace('rgb(', '').replace(')', '')
                            r, g, b = map(int, bg_color.split(','))
                            bg_color = (r, g, b)
                        padding = self.config['subtitle'].getint('background_padding', 15)
                        
                        # Tính kích thước background
                        bg_width = txt_clip.size[0] + padding * 2
                        bg_height = txt_clip.size[1] + padding * 2
                        
                        # Tạo background đơn giản
                        bg_clip = ColorClip(size=(bg_width, bg_height), color=bg_color)
                        bg_clip = bg_clip.set_opacity(background_opacity)
                        
                        # Đặt text vào giữa background
                        txt_clip = txt_clip.set_position(('center', 'center'))
                        
                        # Kết hợp background và text
                        txt_clip = CompositeVideoClip([bg_clip, txt_clip])
                    
                    # Đặt vị trí
                    if position == 'bottom':
                        y_pos = self.height - margin_bottom - txt_clip.size[1]
                        txt_clip = txt_clip.set_position(('center', y_pos))
                    elif position == 'top':
                        txt_clip = txt_clip.set_position(('center', margin_bottom))
                    elif position == 'center':
                        txt_clip = txt_clip.set_position('center')
                    else:  # custom
                        x_pos = self.config['subtitle'].getint('x_position', 0)
                        y_pos = self.config['subtitle'].getint('y_position', 0)
                        txt_clip = txt_clip.set_position((x_pos, y_pos))
                    
                    # Đặt thời gian
                    txt_clip = txt_clip.set_start(sub['start']).set_duration(sub['end'] - sub['start'])
                    
                    subtitle_clips.append(txt_clip)
                    
                except Exception as e:
                    self.progress.print_warning(f"Lỗi khi tạo subtitle clip: {str(e)}")
                    continue
            
            # Ghép các subtitle clip
            if subtitle_clips:
                final_subtitle = CompositeVideoClip(subtitle_clips)
                # Kết hợp với video màu đen
                final_video = CompositeVideoClip([black_clip, final_subtitle])
            else:
                final_video = black_clip
            
            # Lưu video subtitle tạm
            subtitle_path = os.path.join(temp_dir, "temp_subtitle.mp4")
            self.progress.print_message(f"Đang ghi video subtitle: {subtitle_path}")
            
            # Ghi video subtitle
            final_video.write_videofile(
                subtitle_path,
                fps=self.fps,
                codec="libx264",
                audio_codec="aac",
                preset="ultrafast",
                bitrate=self.bitrate,
                threads=1,
                verbose=False,
                logger=None
            )
            
            # Đóng các clip
            black_clip.close()
            if subtitle_clips:
                for clip in subtitle_clips:
                    clip.close()
                final_subtitle.close()
            final_video.close()
            
            return subtitle_path
            
        except Exception as e:
            self.progress.print_error(f"Lỗi khi tạo video subtitle: {str(e)}")
            return None

    def create_video(self, output_dir, temp_audio_path, temp_final_audio_path, subtitles=None):
        """Tạo video từ ảnh và audio"""
        try:
            # Tạo thư mục output nếu chưa tồn tại
            output_dir = os.path.abspath(output_dir)
            os.makedirs(output_dir, exist_ok=True)
            
            # Lấy đường dẫn tuyệt đối cho file output
            output_file = os.path.abspath(self.config["video"].get("output_file", "output_video.mp4"))
            if not output_file.startswith(output_dir):
                output_file = os.path.join(output_dir, os.path.basename(output_file))
            
            self.progress.print_message(f"Đang tạo video tại: {output_file}")
            
            # Kiểm tra và chuyển đổi đường dẫn audio thành đường dẫn tuyệt đối
            temp_audio_path = os.path.abspath(temp_audio_path)
            temp_final_audio_path = os.path.abspath(temp_final_audio_path)
            
            # Kiểm tra file audio tồn tại
            if not os.path.exists(temp_final_audio_path):
                raise FileNotFoundError(f"Không tìm thấy file audio: {temp_final_audio_path}")
                
            if os.path.getsize(temp_final_audio_path) == 0:
                raise Exception("File audio rỗng")
                
            self.progress.print_message(f"Đã xác nhận file audio: {temp_final_audio_path}")
            
            # Lấy thời lượng audio để tính số lượng ảnh cần thiết
            audio_clip = AudioFileClip(temp_final_audio_path)
            audio_duration = audio_clip.duration
            audio_clip.close()
            
            # Tạo video clip từ ảnh với thời lượng phù hợp với audio
            self.progress.print_message("Đang tạo video từ ảnh...")
            video_clip = self.create_video_from_images(output_dir, audio_duration)
            
            if video_clip is None:
                raise Exception("Không thể tạo video clip từ ảnh")
            
            # Tải audio
            audio_clip = AudioFileClip(temp_final_audio_path)
            
            # Thêm audio vào video
            video_clip = video_clip.set_audio(audio_clip)
            
            # Thêm subtitle nếu có
            if subtitles:
                self.progress.print_message("Đang thêm subtitle vào video...")
                
                # Lấy cấu hình subtitle
                font = self.config['subtitle'].get('font', 'Arial')
                font_size = self.config['subtitle'].getint('font_size', 44)
                color = self.config['subtitle'].get('color', '#FFFFFF')
                stroke_color = self.config['subtitle'].get('stroke_color', '#000000')
                stroke_width = self.config['subtitle'].getint('stroke_width', 0)
                position = self.config['subtitle'].get('position', 'bottom')
                margin_bottom = self.config['subtitle'].getint('margin_bottom', 50)
                background_opacity = self.config['subtitle'].getfloat('background_opacity', 0.7)
                
                # Tạo các text clip
                text_clips = []
                for sub in subtitles:
                    try:
                        # Tạo text clip
                        txt_clip = TextClip(
                            sub['text'],
                            fontsize=font_size,
                            font=font,
                            color=color,
                            stroke_color=stroke_color,
                            stroke_width=stroke_width,
                            method='label',
                            align='center'
                        )
                        
                        # Tạo background nếu cần
                        if background_opacity > 0:
                            # Tạo background clip
                            bg_color = self.config['subtitle'].get('background_color', 'rgb(255,236,67)')
                            # Chuyển đổi chuỗi rgb thành tuple
                            if bg_color.startswith('rgb('):
                                bg_color = bg_color.replace('rgb(', '').replace(')', '')
                                r, g, b = map(int, bg_color.split(','))
                                bg_color = (r, g, b)
                            padding = self.config['subtitle'].getint('background_padding', 15)
                            
                            # Tính kích thước background
                            bg_width = txt_clip.size[0] + padding * 2
                            bg_height = txt_clip.size[1] + padding * 2
                            
                            # Tạo background đơn giản
                            bg_clip = ColorClip(size=(bg_width, bg_height), color=bg_color)
                            bg_clip = bg_clip.set_opacity(background_opacity)
                            
                            # Đặt text vào giữa background
                            txt_clip = txt_clip.set_position(('center', 'center'))
                            
                            # Kết hợp background và text
                            txt_clip = CompositeVideoClip([bg_clip, txt_clip])
                        
                        # Đặt vị trí
                        if position == 'bottom':
                            y_pos = self.height - margin_bottom - txt_clip.size[1]
                            txt_clip = txt_clip.set_position(('center', y_pos))
                        elif position == 'top':
                            txt_clip = txt_clip.set_position(('center', margin_bottom))
                        elif position == 'center':
                            txt_clip = txt_clip.set_position('center')
                        else:  # custom
                            x_pos = self.config['subtitle'].getint('x_position', 0)
                            y_pos = self.config['subtitle'].getint('y_position', 0)
                            txt_clip = txt_clip.set_position((x_pos, y_pos))
                        
                        # Đặt thời gian
                        txt_clip = txt_clip.set_start(sub['start']).set_duration(sub['end'] - sub['start'])
                        
                        text_clips.append(txt_clip)
                        
                    except Exception as e:
                        self.progress.print_warning(f"Lỗi khi tạo text clip: {str(e)}")
                        continue
                
                # Kết hợp video và text clips
                if text_clips:
                    video_clip = CompositeVideoClip([video_clip] + text_clips)
            
            # Ghi video cuối cùng
            self.progress.print_message(f"Đang ghi video vào: {output_file}")
            video_clip.write_videofile(
                output_file,
                fps=self.fps,
                codec='libx264',
                audio_codec='aac',
                bitrate=self.bitrate,
                threads=1,
                preset='ultrafast',
                ffmpeg_params=['-loglevel', 'error'],
                logger=None
            )
            
            # Đóng các clip
            video_clip.close()
            audio_clip.close()
            
            # Xóa các file tạm
            self.cleanup_temp_files()
            
            self.progress.print_message(f"Đã tạo video thành công: {output_file}")
            
        except Exception as e:
            self.progress.print_error(f"Lỗi khi tạo video: {str(e)}")
            raise

    def create_video_from_images(self, output_dir, audio_duration):
        """Tạo video clip từ danh sách ảnh"""
        try:
            temp_video_clips = []
            temp_dir = os.path.abspath(os.path.join(output_dir, "temp"))
            os.makedirs(temp_dir, exist_ok=True)
            
            # Lấy danh sách ảnh
            image_dir = os.path.abspath(self.image_dir)
            if not os.path.exists(image_dir):
                raise FileNotFoundError(f"Thư mục ảnh không tồn tại: {image_dir}")
                
            image_files = sorted(
                [f for f in os.listdir(image_dir)
                 if f.lower().endswith((".png", ".jpg", ".jpeg"))]
            )
            
            if not image_files:
                raise FileNotFoundError("Không tìm thấy file ảnh nào.")
                
            # Tính thời lượng video một lần chạy
            single_run_duration = len(image_files) * self.image_duration
            
            # Tính số lần cần lặp lại video
            n_repeats = int(np.ceil(audio_duration / single_run_duration))
            
            self.progress.print_message(f"Thời lượng video một lần chạy: {single_run_duration:.2f}s")
            self.progress.print_message(f"Thời lượng audio: {audio_duration:.2f}s")
            self.progress.print_message(f"Cần lặp lại video {n_repeats} lần")
            
            # Lặp lại danh sách ảnh theo số lần cần thiết
            image_files = image_files * n_repeats
            
            # Tính số lượng ảnh cần thiết dựa trên thời lượng audio
            required_images = int(np.ceil(audio_duration / self.image_duration))
            
            # Cắt bớt ảnh nếu nhiều hơn cần thiết
            if len(image_files) > required_images:
                self.progress.print_message(f"Có {len(image_files)} ảnh, chỉ cần {required_images} ảnh để khớp với audio {audio_duration:.2f}s")
                image_files = image_files[:required_images]
            
            self.progress.print_message(f"Sử dụng {len(image_files)} ảnh để tạo video")
            
            # Xử lý đa luồng
            with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                futures = []
                for i, img_file in enumerate(image_files):
                    futures.append(executor.submit(self.process_image, img_file, i, temp_dir))
                    
                for future in as_completed(futures):
                    output_path = future.result()
                    if output_path and os.path.exists(output_path):
                        temp_video_clips.append(output_path)
            
            if not temp_video_clips:
                raise Exception("Không thể tạo bất kỳ video clip nào từ ảnh.")
                
            # Tạo file danh sách cho ffmpeg
            concat_file = os.path.join(temp_dir, "concat.txt")
            with open(concat_file, "w") as f:
                for clip in temp_video_clips:
                    f.write(f"file '{clip}'\n")
            
            # Sử dụng ffmpeg để ghép các video clips
            self.progress.print_message(f"Đang ghép {len(temp_video_clips)} video clips...")
     
            
            # Tạo video tạm
            temp_video_path = os.path.join(temp_dir, "temp_video.mp4")
            
            # Tạo lệnh ffmpeg
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                '-y',
                temp_video_path
            ]
            
            # Chạy lệnh ffmpeg
            subprocess.run(cmd, check=True)
            
            # Tải video đã ghép
            final_video = VideoFileClip(temp_video_path)
            if final_video is None:
                raise Exception("Không thể tải video đã ghép")
            
            # Lưu danh sách các file tạm để xóa sau
            self.temp_files = temp_video_clips + [concat_file, temp_video_path]
            
            return final_video
            
        except Exception as e:
            self.progress.print_error(f"Lỗi khi tạo video từ ảnh: {str(e)}")
            raise 

    def generate_subtitles_from_audio(self, audio_path):
        """Tạo subtitle tự động từ audio sử dụng Whisper"""
        self.progress.print_message("Đang tạo subtitle từ audio...")
        subtitles = []

        try:
            # ... (giữ nguyên code cũ) ...

            if subtitles:
                try:
                    # Lấy thư mục chứa exe
                    if getattr(sys, 'frozen', False):
                        # Nếu là exe (PyInstaller)
                        exe_dir = os.path.dirname(sys.executable)
                    else:
                        # Nếu là script python
                        exe_dir = os.path.dirname(os.path.abspath(__file__))

                    # Tạo thư mục output nếu chưa có
                    output_dir = os.path.join(exe_dir, "output")
                    os.makedirs(output_dir, exist_ok=True)

                    # Tạo file subtitle trong thư mục output
                    subtitle_path = os.path.join(output_dir, "temp_subtitle.srt")
                    
                    self.progress.print_message(f"Đang lưu subtitle vào: {subtitle_path}")
                    
                    # Lưu file subtitle
                    with open(subtitle_path, 'w', encoding='utf-8') as f:
                        for i, sub in enumerate(subtitles, 1):
                            start = self.format_time(sub['start'])
                            end = self.format_time(sub['end'])
                            f.write(f"{i}\n")
                            f.write(f"{start} --> {end}\n")
                            f.write(f"{sub['text']}\n\n")
                    
                    self.progress.print_message(f"Đã lưu subtitle tại: {subtitle_path}")
                    return subtitle_path

                except Exception as e:
                    self.progress.print_error(f"Lỗi khi lưu file subtitle: {str(e)}")
                    return None

            return subtitles

        except Exception as e:
            self.progress.print_error(f"Lỗi khi tạo subtitle: {str(e)}")
            return None

    def format_time(self, seconds):
        """Chuyển đổi thời gian từ giây sang định dạng SRT"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        seconds = int(seconds)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}" 