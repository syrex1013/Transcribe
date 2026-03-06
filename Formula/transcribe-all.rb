class TranscribeAll < Formula
  include Language::Python::Virtualenv

  desc "CLI audio transcription via Groq Whisper with optional speaker diarization"
  homepage "https://github.com/syrex1013/Transcribe"
  url "https://github.com/syrex1013/Transcribe/archive/refs/tags/v0.4.0.tar.gz"
  version "0.4.0"
  sha256 "b80d1937ceea2c1ba663b80984c38c9673cd00ab37e3a381f529d9b4b84f7732"
  license "MIT"

  depends_on "ffmpeg"
  depends_on "python@3.12"

  resource "certifi" do
    url "https://github.com/syrex1013/Transcribe/archive/refs/tags/v0.4.0.tar.gz"
    sha256 "b80d1937ceea2c1ba663b80984c38c9673cd00ab37e3a381f529d9b4b84f7732"
  end

  resource "charset-normalizer" do
    url "https://github.com/syrex1013/Transcribe/archive/refs/tags/v0.4.0.tar.gz"
    sha256 "b80d1937ceea2c1ba663b80984c38c9673cd00ab37e3a381f529d9b4b84f7732"
  end

  resource "idna" do
    url "https://github.com/syrex1013/Transcribe/archive/refs/tags/v0.4.0.tar.gz"
    sha256 "b80d1937ceea2c1ba663b80984c38c9673cd00ab37e3a381f529d9b4b84f7732"
  end

  resource "markdown-it-py" do
    url "https://github.com/syrex1013/Transcribe/archive/refs/tags/v0.4.0.tar.gz"
    sha256 "b80d1937ceea2c1ba663b80984c38c9673cd00ab37e3a381f529d9b4b84f7732"
  end

  resource "mdurl" do
    url "https://github.com/syrex1013/Transcribe/archive/refs/tags/v0.4.0.tar.gz"
    sha256 "b80d1937ceea2c1ba663b80984c38c9673cd00ab37e3a381f529d9b4b84f7732"
  end

  resource "pygments" do
    url "https://github.com/syrex1013/Transcribe/archive/refs/tags/v0.4.0.tar.gz"
    sha256 "b80d1937ceea2c1ba663b80984c38c9673cd00ab37e3a381f529d9b4b84f7732"
  end

  resource "requests" do
    url "https://github.com/syrex1013/Transcribe/archive/refs/tags/v0.4.0.tar.gz"
    sha256 "b80d1937ceea2c1ba663b80984c38c9673cd00ab37e3a381f529d9b4b84f7732"
  end

  resource "rich" do
    url "https://github.com/syrex1013/Transcribe/archive/refs/tags/v0.4.0.tar.gz"
    sha256 "b80d1937ceea2c1ba663b80984c38c9673cd00ab37e3a381f529d9b4b84f7732"
  end

  resource "urllib3" do
    url "https://github.com/syrex1013/Transcribe/archive/refs/tags/v0.4.0.tar.gz"
    sha256 "b80d1937ceea2c1ba663b80984c38c9673cd00ab37e3a381f529d9b4b84f7732"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "usage", shell_output("#{bin}/transcribe --help").downcase
  end
end
