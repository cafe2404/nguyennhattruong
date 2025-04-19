import os
import configparser
import whisper
from audio_processor import AudioProcessor
from video_processor import VideoProcessor
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

class VideoCreator:
    def __init__(self, config_file="config.ini"):
        self.config = self.load_config(config_file)
        self.progress = ProgressManager()
        self.setup_whisper_config()
        self.audio_processor = AudioProcessor(self.config)
        self.video_processor = VideoProcessor(self.config)

    def load_config(self, config_file):
        """Đọc file cấu hình"""
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Không tìm thấy file cấu hình: {config_file}")

        config = configparser.ConfigParser()
        config.read(config_file, encoding="utf-8")
        return config

    def setup_whisper_config(self):
        """Cấu hình cho Whisper"""
        sub_config = self.config["subtitle"]
        self.whisper_model = sub_config.get("model", "base")
        self.whisper_language = sub_config.get("language", "vi")

    
    def generate_subtitles_from_audio(self, audio_path):
        """Tạo subtitle tự động từ audio sử dụng Whisper"""
        self.progress.print_message("Đang tạo subtitle từ audio...")
        subtitles = []

        try:
            # Thực hiện nhận dạng với Whisper
            model = whisper.load_model(self.whisper_model)
            result = model.transcribe(
                audio_path,
                language=self.whisper_language,
                task="transcribe",
                fp16=True,
                verbose=False
            )

            # Xử lý kết quả theo segments
            segments = result["segments"]
            for segment in segments:
                text = segment["text"].strip()
                if text:
                    subtitles.append({
                        "text": text,
                        "start": segment["start"],
                        "end": segment["end"]
                    })

            self.progress.print_message(f"Đã tạo được {len(subtitles)} subtitle")
            return subtitles
            
        except Exception as e:
            self.progress.print_error(f"Lỗi khi tạo subtitle: {str(e)}")
            return subtitles

    def create_video(self):
        """Tạo video hoàn chỉnh"""
        try:
            # Tạo thư mục output nếu chưa tồn tại
            output_dir = os.path.dirname(os.path.abspath(self.config["video"].get("output_file", "output_video.mp4")))
            if not output_dir:
                output_dir = os.getcwd()
                self.config["video"]["output_file"] = os.path.join(output_dir, "output_video.mp4")
            
            os.makedirs(output_dir, exist_ok=True)
            self.progress.print_message(f"Đã tạo thư mục output: {output_dir}")

            # Bước 1: Xử lý audio
            self.progress.print_message("\nBước 1: Xử lý audio...")
            temp_audio_path, temp_final_audio_path = self.audio_processor.process_audio(output_dir)
            
            if not os.path.exists(temp_final_audio_path) or not os.path.exists(temp_audio_path):
                raise FileNotFoundError(f"Không tìm thấy file audio: {temp_final_audio_path} hoặc {temp_audio_path}")
            
            # Bước 2: Tạo subtitle từ audio
            self.progress.print_message("\nBước 2: Tạo subtitle...")
            subtitles = self.generate_subtitles_from_audio(temp_audio_path)
            
            # Bước 3: Tạo video
            self.progress.print_message("\nBước 3: Tạo video...")
            self.video_processor.create_video(output_dir, temp_audio_path, temp_final_audio_path, subtitles)
            
            self.progress.print_message("\nHoàn thành!")
            
        except Exception as e:
            self.progress.print_error(f"Lỗi trong quá trình xử lý: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        creator = VideoCreator("config.ini")
        creator.create_video()
    except Exception as e:
        print(f"Lỗi: {str(e)}") 