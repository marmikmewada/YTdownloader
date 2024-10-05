import sys
from PyQt5 import QtWidgets, QtCore
from yt_dlp import YoutubeDL
import os
import re

def create_line_edit(placeholder):
    line_edit = QtWidgets.QLineEdit()
    line_edit.setPlaceholderText(placeholder)
    line_edit.setStyleSheet("padding: 10px; border-radius: 5px; border: 1px solid #61dafb;")
    return line_edit

def create_combo_box(items=None):
    combo_box = QtWidgets.QComboBox()
    if items:
        combo_box.addItems(items)
    combo_box.setStyleSheet("padding: 10px; border-radius: 5px; border: 1px solid #61dafb;")
    return combo_box

def create_button(text, callback):
    button = QtWidgets.QPushButton(text)
    button.clicked.connect(callback)
    button.setStyleSheet("background-color: #61dafb; padding: 10px; border-radius: 5px;")
    return button

def fetch_formats(link, status_label, format_selection, progress_bar):
    if not link:
        status_label.setText('Please enter a link first.')
        return

    status_label.setText('Fetching formats...')
    progress_bar.setValue(0)

    def run_fetcher():
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(link, download=False)
                formats = filter_formats(info.get('formats', []))
                on_formats_fetched(formats, format_selection, status_label)
            except Exception as e:
                print(f"Error fetching formats: {str(e)}")
                status_label.setText('Error fetching formats.')
                format_selection.clear()

    QtCore.QThread(run_fetcher).start()

def filter_formats(formats):
    if not isinstance(formats, list):
        print(f"Unexpected formats type: {type(formats)}")
        return []
    common_formats = ['mp4', 'webm', 'mp3', 'm4a']
    return [f for f in formats if isinstance(f, dict) and f.get('ext') in common_formats]

def on_formats_fetched(formats, format_selection, status_label):
    format_selection.clear()
    for fmt in formats:
        format_selection.addItem(f"{fmt.get('format_id', 'N/A')} - {fmt.get('ext', 'N/A')} ({fmt.get('format_note', 'N/A')})")
    format_selection.setEnabled(True)
    status_label.setText('Formats fetched. Please select one to download.')

def download_video(link, available_formats, format_selection, status_label, progress_bar, video_list):
    if not link:
        status_label.setText('Please enter a link first.')
        return

    if not available_formats:
        status_label.setText('Please fetch formats first.')
        return

    selected_index = format_selection.currentIndex()
    if selected_index < 0:
        status_label.setText('Please select a format.')
        return

    selected_format = available_formats[selected_index]
    if not isinstance(selected_format, dict):
        status_label.setText('Error: Selected format is not valid.')
        print(f"Invalid selected_format type: {type(selected_format)}")
        return

    default_filename = sanitize_filename(selected_format.get('title', 'video')) + f".{selected_format.get('ext', 'mp4')}"
    save_path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Save Video", default_filename, "Video Files (*.mp4 *.mkv *.webm);;All Files (*)")

    if not save_path:
        status_label.setText('Download canceled.')
        return

    download_youtube(link, selected_format, save_path, status_label, progress_bar, video_list)

def sanitize_filename(title):
    return re.sub(r'[<>:"/\\|?*]', '_', title)

def download_youtube(link, selected_format, save_path, status_label, progress_bar, video_list):
    format_id = selected_format.get('format_id')
    if not format_id:
        status_label.setText('Error: Format ID is missing.')
        return

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': save_path,
        'progress_hooks': [lambda d: hook(d, status_label, progress_bar, video_list)],
    }

    with YoutubeDL(ydl_opts) as ydl:
        try:
            download_info = ydl.extract_info(link, download=True)
            if not isinstance(download_info, dict):
                raise ValueError(f"Expected download_info to be a dict, got {type(download_info)}")

            status_label.setText('Video downloaded successfully.')
            video_list.addItem(os.path.basename(save_path))
        except Exception as e:
            status_label.setText(f'Error: {str(e)}')
            print(f"Download error: {str(e)}")

def hook(d, status_label, progress_bar, video_list):
    if d.get('status') == 'finished':
        filename = d.get('filename', 'Unknown file')
        print(f"\nDone downloading: {filename}")
        status_label.setText('Download completed.')
        progress_bar.setValue(100)
    elif d.get('status') == 'downloading':
        p = d.get('_percent_str', '0%').replace('%', '')
        try:
            progress = int(float(p))
            progress_bar.setValue(progress)
            status_label.setText(f"Downloading: {progress}%")
        except ValueError:
            status_label.setText("Downloading...")

def main():
    app = QtWidgets.QApplication(sys.argv)

    window = QtWidgets.QWidget()
    window.setWindowTitle('YT downloader by Marmik Mewada')
    window.setMinimumSize(400, 300)
    window.setStyleSheet("background-color: #282c34; color: #ffffff; border: 1px solid #61dafb; border-radius: 10px;")
    layout = QtWidgets.QVBoxLayout()
    layout.setSpacing(20)
    layout.setContentsMargins(20, 20, 20, 20)

    link_input = create_line_edit('Enter link...')
    layout.addWidget(link_input)

    download_option = create_combo_box(["YouTube"])
    layout.addWidget(download_option)

    format_selection = create_combo_box()
    format_selection.setEnabled(False)
    layout.addWidget(format_selection)

    status_label = QtWidgets.QLabel('', window)
    layout.addWidget(status_label)

    progress_bar = QtWidgets.QProgressBar(window)
    progress_bar.setRange(0, 100)
    layout.addWidget(progress_bar)

    video_list = QtWidgets.QListWidget(window)
    layout.addWidget(video_list)

    fetch_formats_button = create_button('Fetch Formats', lambda: fetch_formats(link_input.text(), status_label, format_selection, progress_bar))
    layout.addWidget(fetch_formats_button)

    download_button = create_button('Download', lambda: download_video(link_input.text(), format_selection.currentText(), format_selection, status_label, progress_bar, video_list))
    layout.addWidget(download_button)

    window.setLayout(layout)
    window.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowMinMaxButtonsHint)
    window.setAttribute(QtCore.Qt.WA_DeleteOnClose)

    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
  
