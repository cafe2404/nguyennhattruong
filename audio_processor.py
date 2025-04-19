import os
import numpy as np
from moviepy.editor import AudioFileClip, concatenate_audioclips, CompositeAudioClip
import json
import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

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

class AudioProcessor:
    def __init__(self, config):
        self.config = config
        self.audio_dir = config["video"].get("audio_dir", "audios")
        self.background_music = config["video"].get("background_music", "")
        self.background_music_volume = config["video"].getfloat("background_music_volume", 0.3)
        self.progress = ProgressManager()

    def process_audio(self, output_dir):
        """Xử lý toàn bộ audio và trả về đường dẫn file audio cuối cùng"""
        temp_audio_path = None
        temp_final_audio_path = None
        
        try:
            # Tạo thư mục temp với đường dẫn tuyệt đối
            temp_dir = os.path.abspath(os.path.join(output_dir, "temp"))
            os.makedirs(temp_dir, exist_ok=True)
            self.progress.print_message(f"Đã tạo thư mục temp: {temp_dir}")
            
            # Bước 1: Ghép các file audio gốc
            self.progress.print_message("\nBước 1: Ghép các file audio gốc...")
            audio_clips = []
            
            # Lấy danh sách file audio với đường dẫn tuyệt đối
            audio_dir = os.path.abspath(self.audio_dir)
            if not os.path.exists(audio_dir):
                raise FileNotFoundError(f"Thư mục audio không tồn tại: {audio_dir}")
                
            audio_files = sorted(
                [f for f in os.listdir(audio_dir)
                 if f.lower().endswith((".mp3", ".wav"))]
            )
            
            if not audio_files:
                raise FileNotFoundError(f"Không tìm thấy file audio nào trong thư mục: {audio_dir}")
                
            self.progress.print_message(f"Tìm thấy {len(audio_files)} file audio")
            
            # Tải từng file audio
            for audio_file in audio_files:
                try:
                    audio_path = os.path.join(audio_dir, audio_file)
                    self.progress.print_message(f"Đang xử lý file: {audio_file}")
                    
                    # Kiểm tra file tồn tại và có kích thước
                    if not os.path.exists(audio_path):
                        self.progress.print_warning(f"File không tồn tại: {audio_path}")
                        continue
                        
                    if os.path.getsize(audio_path) == 0:
                        self.progress.print_warning(f"File rỗng: {audio_path}")
                        continue
                        
                    # Tải audio clip
                    clip = AudioFileClip(audio_path)
                    if clip is not None and clip.duration > 0:
                        audio_clips.append(clip)
                        self.progress.print_message(f"Đã tải thành công: {audio_file} (duration: {clip.duration:.2f}s)")
                    else:
                        self.progress.print_warning(f"Không thể tải file audio: {audio_file}")
                        if clip:
                            clip.close()
                            
                except Exception as e:
                    self.progress.print_warning(f"Lỗi khi xử lý file audio {audio_file}: {str(e)}")
                    continue
            
            if not audio_clips:
                raise Exception("Không thể tải bất kỳ file audio nào.")
                
            # Ghép các audio clip
            self.progress.print_message(f"Đang ghép {len(audio_clips)} audio clips...")
            final_audio = concatenate_audioclips(audio_clips)
            
            if final_audio is None or final_audio.duration <= 0:
                raise Exception("Không thể ghép các audio clip.")
                
            self.progress.print_message(f"Đã ghép thành công audio (tổng duration: {final_audio.duration:.2f}s)")
            
            # Lưu audio gốc với đường dẫn tuyệt đối
            temp_audio_path = os.path.join(temp_dir, "temp_audio.mp3")
            self.progress.print_message(f"Đang ghi file audio tạm: {temp_audio_path}")
            
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(temp_audio_path), exist_ok=True)
            
            # Ghi file audio
            final_audio.write_audiofile(
                temp_audio_path,
                fps=44100,
                nbytes=2,
                codec='mp3',
                verbose=False,
                logger=None,
                ffmpeg_params=['-loglevel', 'error']
            )
            
            # Đóng audio clip gốc
            final_audio.close()
            final_audio = None
            
            # Đợi file được ghi xong
            time.sleep(2)
            
            # Kiểm tra file đã được tạo
            if not os.path.exists(temp_audio_path):
                raise Exception(f"Không thể tạo file audio tạm tại: {temp_audio_path}")
                
            if os.path.getsize(temp_audio_path) == 0:
                raise Exception("File audio tạm rỗng")
                
            self.progress.print_message(f"Đã ghi file audio tạm thành công: {temp_audio_path}")
            
            # Bước 2: Thêm nhạc nền
            if self.background_music and os.path.exists(self.background_music):
                self.progress.print_message("\nBước 2: Thêm nhạc nền...")
                try:
                    # Tải audio gốc và nhạc nền với đường dẫn tuyệt đối
                    original_audio = AudioFileClip(temp_audio_path)
                    bg_music = AudioFileClip(os.path.abspath(self.background_music))
                    
                    if original_audio is None or bg_music is None:
                        raise Exception("Không thể tải audio để xử lý nhạc nền")
                        
                    # Điều chỉnh âm lượng
                    original_audio = original_audio.volumex(2.0)  # Tăng âm lượng audio gốc lên 200%
                    bg_music = bg_music.volumex(self.background_music_volume * 0.2)  # Giảm nhạc nền xuống 20%
                    
                    # Lặp nhạc nền nếu cần
                    if bg_music.duration < original_audio.duration:
                        n_repeats = int(np.ceil(original_audio.duration / bg_music.duration))
                        bg_music = concatenate_audioclips([bg_music] * n_repeats)
                    
                    # Cắt nhạc nền cho vừa với audio chính
                    bg_music = bg_music.subclip(0, original_audio.duration)
                    
                    # Trộn âm thanh
                    final_audio = CompositeAudioClip([original_audio, bg_music])
                    final_audio = final_audio.volumex(1.5)  # Tăng tổng âm lượng lên 150%
                    
                    # Lưu audio cuối cùng với đường dẫn tuyệt đối
                    temp_final_audio_path = os.path.join(temp_dir, "temp_final_audio.mp3")
                    self.progress.print_message(f"Đang ghi file audio cuối cùng: {temp_final_audio_path}")
                    
                    # Đảm bảo thư mục tồn tại
                    os.makedirs(os.path.dirname(temp_final_audio_path), exist_ok=True)
                    
                    # Ghi file audio
                    final_audio.write_audiofile(
                        temp_final_audio_path,
                        fps=44100,
                        nbytes=2,
                        codec='mp3',
                        verbose=False,
                        logger=None,
                        ffmpeg_params=['-loglevel', 'error']
                    )
                    
                    # Đóng các audio clip
                    original_audio.close()
                    bg_music.close()
                    final_audio.close()
                    final_audio = None
                    
                    # Đợi file được ghi xong
                    time.sleep(2)
                    
                    # Kiểm tra file đã được tạo
                    if not os.path.exists(temp_final_audio_path):
                        raise Exception(f"Không thể tạo file audio cuối cùng tại: {temp_final_audio_path}")
                        
                    if os.path.getsize(temp_final_audio_path) == 0:
                        raise Exception("File audio cuối cùng rỗng")
                        
                    self.progress.print_message(f"Đã ghi file audio cuối cùng thành công: {temp_final_audio_path}")
                    
                except Exception as e:
                    self.progress.print_warning(f"Lỗi khi xử lý nhạc nền: {str(e)}")
                    # Nếu có lỗi, sử dụng audio gốc
                    temp_final_audio_path = temp_audio_path
                    
            else:
                # Nếu không có nhạc nền, sử dụng audio gốc
                temp_final_audio_path = temp_audio_path
                
            # Kiểm tra lần cuối trước khi trả về
            if not os.path.exists(temp_final_audio_path):
                raise Exception(f"File audio cuối cùng không tồn tại: {temp_final_audio_path}")
                
            if os.path.getsize(temp_final_audio_path) == 0:
                raise Exception("File audio cuối cùng rỗng")
                
            self.progress.print_message(f"Đã xác nhận file audio cuối cùng: {temp_final_audio_path}")
            return temp_audio_path, temp_final_audio_path
            
        except Exception as e:
            self.progress.print_error(f"Lỗi trong quá trình xử lý audio: {str(e)}")
            raise 

    def generate_subtitles_from_audio(self, audio_path):
        """Tạo subtitle tự động từ audio sử dụng Whisper"""
        self.progress.print_message("Đang tạo subtitle từ audio...")
        subtitles = []

        def log_error(step, error):
            import traceback
            error_msg = f"Lỗi ở bước {step}: {str(error)}\n"
            error_msg += f"Chi tiết lỗi:\n{traceback.format_exc()}"
            self.progress.print_error(error_msg)

        try:
            # Bước 1: Kiểm tra file audio
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Không tìm thấy file audio: {audio_path}")
            
            self.progress.print_message(f"File audio: {audio_path}")
            self.progress.print_message(f"Kích thước file: {os.path.getsize(audio_path)} bytes")

            # Bước 2: Kiểm tra model
            if self.whisper_model is None:
                raise ValueError("Model Whisper chưa được khởi tạo")
            
            self.progress.print_message(f"Model Whisper: {type(self.whisper_model).__name__}")
            self.progress.print_message(f"Language: {self.whisper_language}")

            # Bước 3: Transcribe audio
            try:
                self.progress.print_message("Bắt đầu transcribe audio...")
                result = self.whisper_model.transcribe(
                    audio_path,
                    language=self.whisper_language,
                    task="transcribe",
                    fp16=True,
                    verbose=True
                )
                self.progress.print_message("Transcribe hoàn thành")
            except Exception as e:
                log_error("transcribe", e)
                return subtitles

            # Bước 4: Xử lý kết quả
            try:
                if "segments" not in result:
                    raise ValueError("Kết quả transcribe không có segments")
                
                segments = result["segments"]
                self.progress.print_message(f"Số segments nhận được: {len(segments)}")

                for i, segment in enumerate(segments, 1):
                    try:
                        text = segment["text"].strip()
                        if text:
                            subtitles.append({
                                "text": text,
                                "start": segment["start"],
                                "end": segment["end"]
                            })
                    except Exception as e:
                        self.progress.print_warning(f"Lỗi xử lý segment {i}: {str(e)}")
                        continue

                self.progress.print_message(f"Đã tạo được {len(subtitles)} subtitle")
                
            except Exception as e:
                log_error("xử lý segments", e)
                return subtitles

            return subtitles

        except Exception as e:
            log_error("khởi tạo", e)
            return subtitles 