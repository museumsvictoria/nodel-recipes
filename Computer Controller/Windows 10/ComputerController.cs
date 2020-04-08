using System;
using System.Threading.Tasks;
using System.Runtime.InteropServices;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.Windows.Forms;
using System.IO;
using System.Text;

class ComputerController
{
    static bool s_running = true;

    static void Main(string[] args)
    {
        Console.OutputEncoding = System.Text.Encoding.UTF8;
        Console.ForegroundColor = ConsoleColor.Blue;
        Console.WriteLine("// ʕ•ᴥ•ʔ");
        Console.ResetColor();
        Console.WriteLine("// Computer Controller started");

        AppDomain.CurrentDomain.ProcessExit += new EventHandler(CurrentDomain_ProcessExit);

        PollCPU();

        PollVolumeAndMuteChanges();

        PollAudioMeter();

        TakeScreenshots();

        ProcessStandardInput();
    }

    static void CurrentDomain_ProcessExit(object sender, EventArgs e)
    {
        s_running = false;
        Console.WriteLine("// Computer Controller exited");
    }

    static void PrintUsage()
    {
        Console.WriteLine("// get-mute");
        Console.WriteLine("// set-mute (0 or 1)");
        Console.WriteLine("// get-volume (-∞ to 0.0 dB or more depending on hardware)");
        Console.WriteLine("// set-volume (-∞ to 0.0 dB or more depending on hardware)");
        Console.WriteLine("// get-volumescalar (0 - 100)");
        Console.WriteLine("// set-volumescalar (0 - 100)");
        Console.WriteLine("// q");
    }

    static async void ProcessStandardInput()
    {
        while (s_running)
        {
            Task<string> task = Console.In.ReadLineAsync();

            var line = await task;

            if (string.IsNullOrWhiteSpace(line))
                continue;

            var parts = line.Split(' ');

            string action = parts[0];
            string arg;

            bool state;

            switch (action)
            {
                case "get-mute":
                    EmitMute();
                    break;

                case "set-mute":
                    arg = parts[1];

                    if (arg == "1")
                        state = true;
                    else if (arg == "0")
                        state = false;
                    else
                        break;

                    Audio.Mute = state;
                    s_mute = state;
                    EmitMute();
                    break;

                case "get-volume":
                    EmitVolume();
                    break;

                case "get-volumescalar":
                    EmitVolumeScalar();
                    break;

                case "set-volume":
                    float value = float.Parse(parts[1]);
                    Audio.Volume = value;
                    s_volume = value;
                    EmitVolume();
                    break;

                case "set-volumescalar":
                    value = float.Parse(parts[1]);
                    Audio.VolumeScalar = value;
                    s_volumeScalar = value;
                    EmitVolumeScalar();
                    break;

                case "q":
                    Console.WriteLine("// Goodbye");
                    return;

                default:
                    PrintUsage();
                    break;
            };
        }

    }

    #region CPU

    static async void PollCPU()
    {
        Console.WriteLine("// ...polling average CPU usage over 10s");

        PerformanceCounter cpuCounter = new PerformanceCounter();
        cpuCounter.CategoryName = "Processor";
        cpuCounter.CounterName = "% Processor Time";
        cpuCounter.InstanceName = "_Total";

        // Get Current Cpu Usage
        var baseSnap = cpuCounter.NextSample();

        var currentCpuUsage = cpuCounter.NextValue();

        while (s_running)
        {
            await Task.Delay(10000); // check every 10 seconds

            var currentSnap = cpuCounter.NextSample();

            var diff = currentSnap.RawValue - baseSnap.RawValue;

            currentCpuUsage = cpuCounter.NextValue();
            
            Console.WriteLine("{{ event: CPU, arg: {0:0.00} }}", currentCpuUsage);
        }

    }

    #endregion

    #region Audio

    #region (Win32 wrappers, etc.)

    [Guid("C02216F6-8C67-4B5B-9D00-D008E73E0064"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    internal interface IAudioMeterInformation
    {
        int GetPeakValue(out float pfPeak);
    };

    [Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IAudioEndpointVolume
    {
        // f(), g(), ... are unused COM method slots.
        int f(); int g(); int h();
        int SetMasterVolumeLevel(float fLevelDB, Guid pguidEventContext);
        int SetMasterVolumeLevelScalar(float fLevel, Guid pguidEventContext);
        int GetMasterVolumeLevel(ref float pfLevelDB);
        int GetMasterVolumeLevelScalar(ref float pfLevel);
        int j();
        int SetMute([MarshalAs(UnmanagedType.Bool)] bool bMute, Guid pguidEventContext);
        int k(); int s(); int l();
        int GetMute([MarshalAs(UnmanagedType.Bool)] ref bool pbMute);
        int m(); int n(); int i(); int p();
        int GetVolumeRange(out float pflVolumeMindB, out float pflVolumeMaxdB, out float pflVolumeIncrementdB);
    }

    [Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDevice
    {
        [return: MarshalAs(UnmanagedType.IUnknown)]
        object Activate([MarshalAs(UnmanagedType.LPStruct)] Guid iid, int dwClsCtx, IntPtr pActivationParams);
    }

    [Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDeviceEnumerator
    {
        int f(); //  ... unused COM method.
        IMMDevice GetDefaultAudioEndpoint(int dataFlow, int role);
    }

    [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
    class MMDeviceEnumeratorComObject { }

    #endregion

    static bool s_mute = Audio.Mute;

    static float s_volume = Audio.Volume;

    static float s_volumeScalar = Audio.VolumeScalar;

    static void EmitMute()
    {
        Console.WriteLine("{ event: Mute, arg: " + (Audio.Mute ? "true" : "false") + " }");
    }

    static void EmitVolume()
    {
        Console.WriteLine("{{ event: Volume, arg: {0:0.00} }}", Audio.Volume);
    }

    static void EmitVolumeScalar()
    {
        Console.WriteLine("{{ event: VolumeScalar, arg: {0:0.0} }}", Audio.VolumeScalar);
    }

    static async void PollVolumeAndMuteChanges()
    {
        Console.WriteLine("// ...polling volume and mute changes every 2.5s");
        EmitMute(); // initial announcement
        EmitVolume();
        while (s_running)
        {
            // emit values if changed

            var mute = Audio.Mute;
            if (s_mute != mute)
            {
                s_mute = mute;
                EmitMute();
            }

            // only need to poll volume (scalar is linked)
            float volume = Audio.Volume;
            if (s_volume != volume)
            {
                s_volume = volume;
                EmitVolume();

                // scalar will have changed too
                EmitVolumeScalar();
            }

            await Task.Delay(2500); // check every 2.5 seconds
        }
    }

    static async void PollAudioMeter()
    {
        Console.WriteLine("// ...polling audio peak meter every 0.75s");

        while (s_running)
        {
            Console.WriteLine("{{ event: Meter, arg: {0:0.00} }}", Audio.Meter);
            await Task.Delay(750); // check every 0.75 seconds
        }
    }

    public class Audio
    {
        private static IMMDevice device = GetDefaultDevice();
        private static IAudioEndpointVolume endpointVolume = Audio.ActivateEndpointVolume(device);
        private static IAudioMeterInformation meterInformation = Audio.ActivateMeterInformation(device);

        private static IMMDevice GetDefaultDevice()
        {
            var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
            return enumerator.GetDefaultAudioEndpoint(/*eRender*/ 0, /*eMultimedia*/ 1);
        }

        static IAudioMeterInformation ActivateMeterInformation(IMMDevice device)
        {
            return (IAudioMeterInformation)device.Activate(typeof(IAudioMeterInformation).GUID, 0, IntPtr.Zero);
        }

        static IAudioEndpointVolume ActivateEndpointVolume(IMMDevice device)
        {
            return (IAudioEndpointVolume)device.Activate(typeof(IAudioEndpointVolume).GUID, /*CLSCTX_ALL*/ 23, IntPtr.Zero);
        }
        
        public static float Volume // dB
        {
            get { float v = -1; Marshal.ThrowExceptionForHR(Audio.endpointVolume.GetMasterVolumeLevel(ref v)); return v; }
            set { Marshal.ThrowExceptionForHR(Audio.endpointVolume.SetMasterVolumeLevel(value, Guid.Empty)); }
        }

        public static float VolumeScalar // (0 - 100)
        {
            get { float v = -1; Marshal.ThrowExceptionForHR(Audio.endpointVolume.GetMasterVolumeLevelScalar(ref v)); return v * 100.0f; }
            set { Marshal.ThrowExceptionForHR(Audio.endpointVolume.SetMasterVolumeLevelScalar(value / 100.0f, Guid.Empty)); }
        }

        public static bool Mute
        {
            get { bool mute = false; Marshal.ThrowExceptionForHR(Audio.endpointVolume.GetMute(ref mute)); return mute; }
            set { Marshal.ThrowExceptionForHR(Audio.endpointVolume.SetMute(value, System.Guid.Empty)); }
        }

        public static double Meter // dB
        {
            get {
                float v;

                // 0.0 - 1.0 sample amplitude, -∞ to 0 dB
                Marshal.ThrowExceptionForHR(Audio.meterInformation.GetPeakValue(out v));

                // use 0.00158 (≈-96 dB) as threshold for pure digital silence

                return v < 0.00158 ? -96 : 20 * Math.Log10(v);
            }
        }

    }

    #endregion

    #region Screenshots

    public async static void TakeScreenshots()
    {
        Console.WriteLine("// ...taking screenshots after 10s then every 60s");

        await Task.Delay(10000); // first after 10s
        Screenshots();

        while (s_running)
        {
            await Task.Delay(60000); // then every 60s
            Screenshots();
        }
    }

    private static StringBuilder[] s_lastScreenshots; // use this to reduce memory allocation

    public static void Screenshots()
    {
        int i = 0;

        try
        {
            var allScreens = Screen.AllScreens;

            // check if screens come and / or go
            if (s_lastScreenshots == null || s_lastScreenshots.Length != allScreens.Length)
                s_lastScreenshots = new StringBuilder[allScreens.Length];

            foreach (var screen in allScreens)
            {
                Bitmap screenshot = new Bitmap(screen.Bounds.Width, screen.Bounds.Height, PixelFormat.Format32bppArgb);
                Graphics screenshotGraphics = Graphics.FromImage(screenshot);

                // Make the screenshot
                screenshotGraphics.CopyFromScreen(Screen.PrimaryScreen.Bounds.X, Screen.PrimaryScreen.Bounds.Y, 0, 0, Screen.PrimaryScreen.Bounds.Size, CopyPixelOperation.SourceCopy);

                Image newImage = ScaleImage(screenshot, 400, 400);

                // Other types
                // screenshot.Save("screen" + i + ".jpg", GetEncoderInfo("image/jpeg"), p);
                // newImage.Save("screen" + i + ".png", ImageFormat.Png);

                // DON'T SAVE TO DISK
                // screenshot.Save("screen" + i + ".jpg", GetEncoderInfo("image/jpeg"), p);

                using (MemoryStream m = new MemoryStream())
                {
                    // must keep it tiny, fit for thumbnail purposes (nodel not designed to handle large binary blobs)
                    var p = new EncoderParameters(1);
                    p.Param[0] = new EncoderParameter(System.Drawing.Imaging.Encoder.Quality, 10L);
                    newImage.Save(m, GetEncoderInfo("image/jpeg"), p);

                    // for PNG
                    // string contentType = "image/png";
                    // newImage.Save(m, ImageFormat.Png);

                    byte[] imageBytes = m.ToArray();

                    // Convert byte[] to Base64 String
                    string base64String = Convert.ToBase64String(imageBytes, Base64FormattingOptions.None); // or InsertLineBreaks

                    var currentScreenshot = s_lastScreenshots[i];
                    if (currentScreenshot == null)
                    {
                        currentScreenshot = new StringBuilder();
                        s_lastScreenshots[i] = currentScreenshot;
                    }
                    currentScreenshot.Length = 0; // allows reuse of memory if possible
                    currentScreenshot.Append("{ event: Screenshot" + (i + 1) + ", arg: 'data:image/jpeg;base64," + base64String + "' }");

                    var lastScreenshot = s_lastScreenshots[i];

                    Console.WriteLine(currentScreenshot);
                    s_lastScreenshots[i] = currentScreenshot;
                }

                i++;
            }
        }
        catch (Exception)
        {
            // show a generic error screenshot indicating capture problems e.g. when locked
            Console.WriteLine("{ event: Screenshot1, arg: 'data:image/png;base64," + MISSING_IMAGE + "' }");
        }
    }

    private static ImageCodecInfo GetEncoderInfo(String mimeType)
    {
        int j;
        ImageCodecInfo[] encoders;
        encoders = ImageCodecInfo.GetImageEncoders();
        for (j = 0; j < encoders.Length; ++j)
        {
            if (encoders[j].MimeType == mimeType)
                return encoders[j];
        }
        return null;
    }

    public static Image ScaleImage(Image image, int maxWidth, int maxHeight)
    {
        var ratioX = (double)maxWidth / image.Width;
        var ratioY = (double)maxHeight / image.Height;
        var ratio = Math.Min(ratioX, ratioY);

        var newWidth = (int)(image.Width * ratio);
        var newHeight = (int)(image.Height * ratio);

        var newImage = new Bitmap(newWidth, newHeight);

        using (var graphics = Graphics.FromImage(newImage))
        {
            graphics.DrawImage(image, 0, 0, newWidth, newHeight);
        }

        return newImage;
    }

    private static readonly string MISSING_IMAGE = "iVBORw0KGgoAAAANSUhEUgAAAZAAAAGQBAMAAABykSv/AAAAAXNSR0IArs4c6QAA" +
        "AARnQU1BAACxjwv8YQUAAAAwUExURQAAABQMABsQACgYADgiAE8wAGQ9AHRHAI1W" +
        "AJ5hAK5qAMZ6ANB/ANiEAPybAAAAANY6MdIAAAAJcEhZcwAADsMAAA7DAcdvqGQA" +
        "AASfSURBVHja7Zo/i1xVHEBndnYUCYYkjYUoC3YWSzBuL1aiCIkEExc2H8AqwT8E" +
        "BVEwEJTY2NtotAgGhKQJmO8gNhLJNqK77jL3M5idN28zM9nO3/3NecM53Wzxuxzu" +
        "OzP3vbc9ERFZFMdGHWdvInK8dJz9icizpePsL9uOKELBRmgsp0ivo6yXuUZ6HWV9" +
        "GXdEEQI2QkMRGjZCQxEaNkJDERo2QkMRGjZCQxEaNkJDERo2QkMRGjZCQxEaNkJD" +
        "ERo2QkMRGjZCQxEaNkJDERo2QkMRGjZCQxEaNkJDERo2QkMRGjZCQxEaNkJDERo2" +
        "QkMRGjZCQxEaNkJDERo2QkMRGjZCQxEaNkJDERo2QkMRGjZCQxEaNkJDERo2QkMR" +
        "GjZCQxEaNkJDERo2QkMRGjZCQxEaNkJDERo2QkMRGjZCI1dk9d2r1z8+X2V0osjK" +
        "hZ/LmP1rJ+KnpzXS37hRDtl5LXx+1o6sXLxfpvgj3CRJZPDedpnhbvQKOSKrn5Q5" +
        "RleCl0hpZPh1eYLd07FrpOzIC+UIvohdI0Vk/SiRnfg1FiNSzoavUb2RF48UuRO6" +
        "RvKO/Hnv1q/tF/Fu+BrVRdodeXDt/CunXr14u/k0Cr22MkVuvt583JiYfB65RmIj" +
        "Nw9/Od5oRH6LXCNxRy4ffl75ZvyHvyPXSBE5PifSezm+9sRf9qm2V8ffXKPINVIa" +
        "eX5epN9cW5FrpOzIMweD96dvQT4bi0TeKKaIDA8G761N/WVrLBJ5AE4RGdyf/47a" +
        "mr/Y/jc59+xvPir73PQf6orUu0McbN77YOYPTSORN+5ZDx9OzXzqf9fNRp7gqeaM" +
        "shY4cjHPft8qVX8Q03ZkeLujR5Q5+p+Wjh4aZ+lvNh7ll8ip+Y30Dx86Xo4cm78j" +
        "m63HXugjunSR90tLaCLZIoOpdwuhV1ZyI+1jhwN2Yt/2pO7IYOodySh2Q3JFVh97" +
        "lLvBr98WJbIX/coqtZHB4wvrnejZC9qRD8Nn58beevwQP3shO/JthdkLaGT0ZY3Z" +
        "uZfWdvzRpCVXZPzDfqfK7FSR5knp91Vm5561tuIPiy25p9/nHi3w74kqo5OP8ZdK" +
        "uVJncvaN1cZapcH+TyMNRWjYCA1FaCQ30j95stLk3B3ZuPrV9Y9OVxmdKjIcvzr8" +
        "scqpMVXk7eaW/WyN2amNTJ6Y/l5jduaOtE+D/qkxPFNkOBHZrTF8KUVqN9I+n9up" +
        "MTz1W2vy9vCvGrNTRS41IlUeo6SKPD3ekt3qP4j1z1oXbj18+NO5KqOTT78vnTlT" +
        "6TGK9yM0vGenoQgNG6GhCA0boaEIDRuhoQgNG6GhCA0boaEIDRuhoQgNG6GhCA0b" +
        "oaEIDRuhoQgNG6GhCA0boaEIDRuhoQgNG6GhCA0boaEIDRuhoQgNG6GhCA0boaEI" +
        "DRuhoQgNG6GhCA0boaEIDRuhoQgNG6GhCA0boaEIDRuhoQgNG6GhCA0boaEIDRuh" +
        "oQgNG6GhCA0boaEIDRuhoQgNG6GhCA0boaEIDRuhoQgNG6GhCA0boaEIDRuhoQgN" +
        "G6GxvCJdZqaRLrN0O6IIBRuhsXQix7Y7zoOeiIgshF7vPwH61H6gvzjKAAAAAElF" +
        "TkSuQmCC";

    #endregion

}
