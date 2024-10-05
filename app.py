import sys
from PyQt5 import QtWidgets, QtCore, QtGui
from yt_dlp import YoutubeDL
import os
import re

class FormatFetcher(QtCore.QThread):
    formats_fetched = QtCore.pyqtSignal(list)

    def __init__(self, link):
        super().__init__()
        self.link = link

    def run(self):
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(self.link, download=False)
                formats = self.filter_formats(info.get('formats', []))
                self.formats_fetched.emit(formats)
            except Exception as e:
                print(f"Error fetching formats: {str(e)}")
                self.formats_fetched.emit([])

    def filter_formats(self, formats):
        if not isinstance(formats, list):
            print(f"Unexpected formats type: {type(formats)}")
            return []

        common_formats = ['mp4', 'webm', 'mp3', 'm4a']
        return [f for f in formats if isinstance(f, dict) and f.get('ext') in common_formats]

class VideoDownloader(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.downloaded_videos = []
        self.available_formats = []

    def initUI(self):
        self.setWindowTitle('YT downloader by Marmik Mewada')
        self.setMinimumSize(400, 300)
        self.setStyleSheet("background-color: #282c34; color: #ffffff; border: 1px solid #61dafb; border-radius: 10px;")
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        self.link_input = QtWidgets.QLineEdit(self)
        self.link_input.setPlaceholderText('Enter link...')
        self.link_input.setStyleSheet("padding: 10px; border-radius: 5px; border: 1px solid #61dafb;")
        layout.addWidget(self.link_input)

        self.download_option = QtWidgets.QComboBox(self)
        self.download_option.addItems(["YouTube"])
        self.download_option.setStyleSheet("padding: 10px; border-radius: 5px; border: 1px solid #61dafb;")
        layout.addWidget(self.download_option)

        self.format_selection = QtWidgets.QComboBox(self)
        self.format_selection.setEnabled(False)
        self.format_selection.setStyleSheet("padding: 10px; border-radius: 5px; border: 1px solid #61dafb;")
        layout.addWidget(self.format_selection)

        self.fetch_formats_button = QtWidgets.QPushButton('Fetch Formats', self)
        self.fetch_formats_button.clicked.connect(self.fetch_formats)
        self.fetch_formats_button.setStyleSheet("background-color: #61dafb; padding: 10px; border-radius: 5px;")
        layout.addWidget(self.fetch_formats_button)

        self.download_button = QtWidgets.QPushButton('Download', self)
        self.download_button.clicked.connect(self.download_video)
        self.download_button.setStyleSheet("background-color: #61dafb; padding: 10px; border-radius: 5px;")
        layout.addWidget(self.download_button)

        self.status_label = QtWidgets.QLabel('', self)
        layout.addWidget(self.status_label)

        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setStyleSheet("QProgressBar { background-color: #555; border-radius: 5px; } QProgressBar::chunk { background-color: #61dafb; }")
        layout.addWidget(self.progress_bar)

        self.video_list = QtWidgets.QListWidget(self)
        self.video_list.setStyleSheet("background-color: #444; border: none; border-radius: 5px;")
        layout.addWidget(self.video_list)

        self.setLayout(layout)

        # Set window flags to allow resizing and moving
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowMinMaxButtonsHint)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # Optional: Allow moving the window by clicking and dragging
        self.old_pos = self.pos()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.old_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self.old_pos)

    def fetch_formats(self):
        link = self.link_input.text()
        if not link:
            self.status_label.setText('Please enter a link first.')
            return
        
        self.status_label.setText('Fetching formats...')
        self.progress_bar.setValue(0)
        self.format_fetcher = FormatFetcher(link)
        self.format_fetcher.formats_fetched.connect(self.on_formats_fetched)
        self.format_fetcher.start()

    def on_formats_fetched(self, formats):
        self.available_formats = formats
        self.format_selection.clear()
        for fmt in self.available_formats:
            self.format_selection.addItem(f"{fmt.get('format_id', 'N/A')} - {fmt.get('ext', 'N/A')} ({fmt.get('format_note', 'N/A')})")
        self.format_selection.setEnabled(True)
        self.status_label.setText('Formats fetched. Please select one to download.')

    def download_video(self):
        link = self.link_input.text()
        if not link:
            self.status_label.setText('Please enter a link first.')
            return

        if not self.available_formats:
            self.status_label.setText('Please fetch formats first.')
            return

        selected_index = self.format_selection.currentIndex()
        if selected_index < 0:
            self.status_label.setText('Please select a format.')
            return

        selected_format = self.available_formats[selected_index]
        
        if not isinstance(selected_format, dict):
            self.status_label.setText('Error: Selected format is not valid.')
            print(f"Invalid selected_format type: {type(selected_format)}")
            return

        default_filename = f"{self.sanitize_filename(selected_format.get('title', 'video'))}.{selected_format.get('ext', 'mp4')}"
        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Video", default_filename, "Video Files (*.mp4 *.mkv *.webm);;All Files (*)")

        if not save_path:
            self.status_label.setText('Download canceled.')
            return

        self.download_youtube(link, selected_format, save_path)

    def sanitize_filename(self, title):
        return re.sub(r'[<>:"/\\|?*]', '_', title)

    def download_youtube(self, link, selected_format, save_path):
        format_id = selected_format.get('format_id')

        if not format_id:
            self.status_label.setText('Error: Format ID is missing.')
            return

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': save_path,
            'progress_hooks': [self.hook],
        }

        with YoutubeDL(ydl_opts) as ydl:
            try:
                download_info = ydl.extract_info(link, download=True)

                if not isinstance(download_info, dict):
                    raise ValueError(f"Expected download_info to be a dict, got {type(download_info)}")

                self.status_label.setText('Video downloaded successfully.')
                self.downloaded_videos.append(os.path.basename(save_path))
                self.video_list.addItem(os.path.basename(save_path))
            except Exception as e:
                self.status_label.setText(f'Error: {str(e)}')
                print(f"Download error: {str(e)}")

    def hook(self, d):
        if d.get('status') == 'finished':
            filename = d.get('filename', 'Unknown file')
            print(f"\nDone downloading: {filename}")
            self.status_label.setText('Download completed.')
            self.progress_bar.setValue(100)
        elif d.get('status') == 'downloading':
            p = d.get('_percent_str', '0%')
            if isinstance(p, str):
                p = p.replace('%', '')
                try:
                    progress = int(float(p))
                    self.progress_bar.setValue(progress)
                    self.status_label.setText(f"Downloading: {progress}%")
                except ValueError:
                    self.status_label.setText("Downloading...")
            else:
                self.status_label.setText("Downloading...")

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    downloader = VideoDownloader()
    downloader.show()
    sys.exit(app.exec_())
