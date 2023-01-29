using System;
using System.Threading.Tasks;
using System.Runtime.InteropServices;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.Windows.Forms;
using System.IO;
using System.Text;
using System.Management;
using System.Text.RegularExpressions;
using System.Collections.Generic;

// rev. 4: gracefully handles missing audio hardware
//   - if missing at start, will check every min for presence
//   - if found but then goes missing/problematic, will gracefully shutdown avoiding
//     any potentional for memory leaks
//
// rev. 3: fixed partial screenshot capture when DPI not 100%

class ComputerController
{
    static bool s_running = true;

    static void Main(string[] args)
    {
        Console.OutputEncoding = Encoding.UTF8;
        Console.ForegroundColor = ConsoleColor.Blue;
        Console.WriteLine("// ʕ•ᴥ•ʔ");
        Console.ResetColor();
        Console.WriteLine("// Computer Controller started");

        AppDomain.CurrentDomain.ProcessExit += new EventHandler(CurrentDomain_ProcessExit);

        PollCPU();

        TryPollAudio();

        TakeScreenshots();

        PollComputerHardwareInfoOnce();

        ProcessStandardInput();
    }

    static void CurrentDomain_ProcessExit(object sender, EventArgs e)
    {
        s_running = false;
        Console.WriteLine("// Computer Controller exited");
    }

    static void PrintUsage()
    {
        Console.WriteLine("// get-mute (true or false)");
        Console.WriteLine("// set-mute");
        Console.WriteLine("// get-volumerange (min max step)");
        Console.WriteLine("// get-volume (-∞ to 0.0 dB or more depending on hardware)");
        Console.WriteLine("// set-volume");
        Console.WriteLine("// get-volumescalar (0.0 - 100.0)");
        Console.WriteLine("// set-volumescalar");
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

                    if (arg == "true")
                        state = true;
                    else if (arg == "false")
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

        PerformanceCounter cpuCounter = new PerformanceCounter()
        {
            CategoryName = "Processor",
            CounterName = "% Processor Time",
            InstanceName = "_Total"
        };

        // start the poll, first reading will be zero
        var usage = cpuCounter.NextValue();

        while (s_running)
        {
            await Task.Delay(10000); // check every 10 seconds

            usage = cpuCounter.NextValue();
            Console.WriteLine("{{ event: CPU, arg: {0:0.0} }}", usage);
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
        // with help from https://archive.codeplex.com/?p=netcoreaudio

        [PreserveSig] int RegisterControlChangeNotify([In] [MarshalAs(UnmanagedType.Interface)] UIntPtr client);
        [PreserveSig] int UnregisterControlChangeNotify([In] [MarshalAs(UnmanagedType.Interface)] UIntPtr client);
        [PreserveSig] int GetChannelCount([Out] [MarshalAs(UnmanagedType.U4)] out UInt32 channelCount);
        [PreserveSig] int SetMasterVolumeLevel([In] [MarshalAs(UnmanagedType.R4)] float level, [In] [MarshalAs(UnmanagedType.LPStruct)] Guid eventContext);
        [PreserveSig] int SetMasterVolumeLevelScalar([In] [MarshalAs(UnmanagedType.R4)] float level, [In] [MarshalAs(UnmanagedType.LPStruct)] Guid eventContext);
        [PreserveSig] int GetMasterVolumeLevel([Out] [MarshalAs(UnmanagedType.R4)] out float level);
        [PreserveSig] int GetMasterVolumeLevelScalar([Out] [MarshalAs(UnmanagedType.R4)] out float level);
        [PreserveSig] int SetChannelVolumeLevel([In] [MarshalAs(UnmanagedType.U4)] UInt32 channelNumber, [In] [MarshalAs(UnmanagedType.R4)] float level, [In] [MarshalAs(UnmanagedType.LPStruct)] Guid eventContext);
        [PreserveSig] int SetChannelVolumeLevelScalar([In] [MarshalAs(UnmanagedType.U4)] UInt32 channelNumber, [In] [MarshalAs(UnmanagedType.R4)] float level, [In] [MarshalAs(UnmanagedType.LPStruct)] Guid eventContext);
        [PreserveSig] int GetChannelVolumeLevel([In] [MarshalAs(UnmanagedType.U4)] UInt32 channelNumber, [Out] [MarshalAs(UnmanagedType.R4)] out float level);
        [PreserveSig] int GetChannelVolumeLevelScalar([In] [MarshalAs(UnmanagedType.U4)] UInt32 channelNumber, [Out] [MarshalAs(UnmanagedType.R4)] out float level);
        [PreserveSig] int SetMute([In] [MarshalAs(UnmanagedType.Bool)] Boolean isMuted, [In] [MarshalAs(UnmanagedType.LPStruct)] Guid eventContext);
        [PreserveSig] int GetMute([Out] [MarshalAs(UnmanagedType.Bool)] out Boolean isMuted);
        [PreserveSig] int GetVolumeStepInfo([Out] [MarshalAs(UnmanagedType.U4)] out UInt32 step, [Out] [MarshalAs(UnmanagedType.U4)] out UInt32 stepCount);
        [PreserveSig] int VolumeStepUp([In] [MarshalAs(UnmanagedType.LPStruct)] Guid eventContext);
        [PreserveSig] int VolumeStepDown([In] [MarshalAs(UnmanagedType.LPStruct)] Guid eventContext);
        [PreserveSig] int QueryHardwareSupport([Out] [MarshalAs(UnmanagedType.U4)] out UInt32 hardwareSupportMask);
        [PreserveSig] int GetVolumeRange([Out] [MarshalAs(UnmanagedType.R4)] out float volumeMin, [Out] [MarshalAs(UnmanagedType.R4)] out float volumeMax, [Out] [MarshalAs(UnmanagedType.R4)] out float volumeStep);
    }

    public enum DEVICE_STATE : uint
    {
        DEVICE_STATE_ACTIVE = 0x00000001,
        DEVICE_STATE_DISABLED = 0x00000002,
        DEVICE_STATE_NOTPRESENT = 0x00000004,
        DEVICE_STATE_UNPLUGGED = 0x00000008,
        DEVICE_STATEMASK_ALL = 0x0000000f
    }

    [Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDevice
    {
        [return: MarshalAs(UnmanagedType.IUnknown)]
        object Activate([MarshalAs(UnmanagedType.LPStruct)] Guid iid, int dwClsCtx, IntPtr pActivationParams);

        int f(); //  ... unused COM method.

        int GetId([Out][MarshalAs(UnmanagedType.LPWStr)] out string ppstrId);

        int GetState([Out][MarshalAs(UnmanagedType.U4)] out DEVICE_STATE pdwState);
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

    static bool s_mute;

    static float s_volume;

    static float s_volumeScalar;

    static void EmitVolumeRange()
    {
        if (!Audio.TryAudioDevice())
            return;

        float min, max, step;
        Audio.GetVolumeRange(out min, out max, out step);
        Console.WriteLine("{{ event: VolumeRange, arg: {{ min: {0:0.00}, max: {1:0.00}, step:{2:0.00} }} }}", min, max, step);
    }

    static void EmitMute()
    {
        if (!Audio.TryAudioDevice())
            return;

        Console.WriteLine("{ event: Mute, arg: " + (Audio.Mute ? "true" : "false") + " }");
    }

    static void EmitVolume()
    {
        if (!Audio.TryAudioDevice())
            return;

        Console.WriteLine("{{ event: Volume, arg: {0:0.00} }}", Audio.Volume);
    }

    static void EmitVolumeScalar()
    {
        if (!Audio.TryAudioDevice())
            return;

        Console.WriteLine("{{ event: VolumeScalar, arg: {0:0.0} }}", Audio.VolumeScalar);
    }

    static async void TryPollAudio()
    {
        while (s_running)
        {
            if (Audio.TryAudioDevice())
            {
                // at this point if audio goes wrong the process will self-terminate
                // rather than risk resource leaks caused by audio hardware COM references

                Console.WriteLine("// audio hardware found; will exit if audio state changes or problems occur");

                PollVolumeAndMuteChanges();

                PollAudioMeter();

                return;
            }

            Console.WriteLine("// ...checking for audio hardware every 60s");

            await Task.Delay(60000); // check every min
        }
    }

    static async void PollVolumeAndMuteChanges()
    {
        Console.WriteLine("// ...polling volume and mute changes every 5s");

        try
        {
            // initial announcement
            EmitVolumeRange();
            EmitMute();
            EmitVolume();
            EmitVolumeScalar();

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

                await Task.Delay(5000); // check every 5 seconds

                var deviceState = Audio.GetDeviceState();
                if (deviceState != DEVICE_STATE.DEVICE_STATE_ACTIVE)
                {
                    Console.WriteLine("// device audio state is not active, is " + deviceState);
                    throw new Exception("Audio device not active anymore");
                }
            }
        }
        catch (Exception)
        {
            // likely problem with audio device, so shutdown
            Console.WriteLine("// problem, audio device issue? exiting...");
            Environment.Exit(-1);
        }
    }

    static async void PollAudioMeter()
    {
        Console.WriteLine("// ...polling audio peak meter every 0.75s");

        try
        {

            while (s_running)
            {
                Console.WriteLine("{{ event: AudioMeter, arg: {0:0.00} }}", Audio.Meter);
                await Task.Delay(750); // check every 0.75 seconds
            }
        }
        catch (Exception)
        {
            // likely problem with audio device, so shutdown
            Console.WriteLine("// problem, audio device issue? exiting...");
            Environment.Exit(-1);
        }
    }

    public class Audio
    {
        // use of static field and methods is done as cautious approach to COM integration

        private static IMMDevice device;
        private static IAudioEndpointVolume endpointVolume;
        private static IAudioMeterInformation meterInformation;

        public static bool TryAudioDevice()
        {
            try
            {
                if (device != null)
                    return true;

                device = GetDefaultDevice();

                endpointVolume = Audio.ActivateEndpointVolume(device);
                meterInformation = Audio.ActivateMeterInformation(device);
                return true;
            }
            catch (Exception)
            {
                return false;
            }
        }

        static IMMDevice GetDefaultDevice()
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

        public static void GetVolumeRange(out float min, out float max, out float step) // dB
        {
            Marshal.ThrowExceptionForHR(Audio.endpointVolume.GetVolumeRange(out min, out max, out step));
        }

        public static DEVICE_STATE GetDeviceState()
        {
            DEVICE_STATE pdwState; Marshal.ThrowExceptionForHR(device.GetState(out pdwState)); return pdwState;
        }

        public static string GetDeviceId()
        {
            string pdwState; Marshal.ThrowExceptionForHR(device.GetId(out pdwState)); return pdwState;
        }

        public static float Volume // dB
        {
            get { float v = -1; Marshal.ThrowExceptionForHR(Audio.endpointVolume.GetMasterVolumeLevel(out v)); return v; }
            set { Marshal.ThrowExceptionForHR(Audio.endpointVolume.SetMasterVolumeLevel(value, Guid.Empty)); }
        }

        public static float VolumeScalar // (0 - 100)
        {
            get { float v = -1; Marshal.ThrowExceptionForHR(Audio.endpointVolume.GetMasterVolumeLevelScalar(out v)); return v * 100.0f; }
            set { Marshal.ThrowExceptionForHR(Audio.endpointVolume.SetMasterVolumeLevelScalar(value / 100.0f, Guid.Empty)); }
        }

        public static bool Mute
        {
            get { bool mute = false; Marshal.ThrowExceptionForHR(Audio.endpointVolume.GetMute(out mute)); return mute; }
            set { Marshal.ThrowExceptionForHR(Audio.endpointVolume.SetMute(value, Guid.Empty)); }
        }

        public static double Meter // dB
        {
            get
            {
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

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();

    public async static void TakeScreenshots()
    {
        Console.WriteLine("// ...taking screenshots after 10s then every 60s");

        // required when non-100% DPI scaling used
        SetProcessDPIAware();

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
                screenshotGraphics.CopyFromScreen(screen.Bounds.X, screen.Bounds.Y, 0, 0, screen.Bounds.Size, CopyPixelOperation.SourceCopy);

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

    #region Computer hardware info

    static void PollComputerHardwareInfoOnce()
    {
        Console.WriteLine("// ...retrieving computer hardware info once");

        Dictionary<String, object> cache = new Dictionary<string, object>(StringComparer.OrdinalIgnoreCase);
        CacheWMITable("Win32_Processor", cache);
        CacheWMITable("Win32_ComputerSystem", cache);
        CacheWMITable("Win32_PhysicalMemory", cache);

        Object value;

        Console.WriteLine("{{ event: CPUName, arg: {0} }}", IntoQuotedJSONString(cache.TryGetValue("Win32_Processor.name", out value) ? value : ""));
        Console.WriteLine("{{ event: Manufacturer, arg: {0} }}", IntoQuotedJSONString(cache.TryGetValue("Win32_ComputerSystem.Manufacturer", out value) ? value : ""));
        Console.WriteLine("{{ event: SystemFamily, arg: {0} }}", IntoQuotedJSONString(cache.TryGetValue("Win32_ComputerSystem.SystemFamily", out value) ? value : ""));
        Console.WriteLine("{{ event: Model, arg: {0} }}", IntoQuotedJSONString(cache.TryGetValue("Win32_ComputerSystem.Model", out value) ? value : ""));
        Console.WriteLine("{{ event: Cores, arg: {0} }}", IntoQuotedJSONString(cache.TryGetValue("Win32_Processor.NumberOfCores", out value) ? value : ""));
        Console.WriteLine("{{ event: LogicalProcessors, arg: {0} }}", IntoQuotedJSONString(cache.TryGetValue("Win32_Processor.NumberOfLogicalProcessors", out value) ? value : ""));

        cache.TryGetValue("Win32_Processor.MaxClockSpeed", out value);
        Console.WriteLine("{{ event: MaxClockSpeed, arg: \"{0:0.0} GHz\" }}", value is UInt32 ? ((UInt32)value) / 1000.0 : 0);

        cache.TryGetValue("Win32_PhysicalMemory.Capacity", out value);
        Console.WriteLine("{{ event: PhysicalMemory, arg: \"{0:0.0} GB\" }}", value is UInt64 ? ((UInt64)value) / 1024 / 1024 / 1024 : 0);
    }

    // Removes (R), (TM), Inc.
    static readonly Regex STRIP_EXTRANEOUS = new Regex(@"\((R|r|TM|tm)\)|Inc.");

    static void CacheWMITable(String table, Dictionary<String, object> cache)
    {
        using (ManagementObjectSearcher searcher = new ManagementObjectSearcher("SELECT * FROM " + table))
        {
            foreach (ManagementObject mo in searcher.Get())
            {
                using (mo)
                {
                    foreach (var entry in mo.Properties)
                    {
                        var value = entry.Value;
                        var text = value as String;

                        if (text != null)
                            text = STRIP_EXTRANEOUS.Replace(text, "").Trim().Replace("  ", " ");

                        var key = table + "." + entry.Name;
                        if (!String.IsNullOrWhiteSpace(text))
                            cache[key] = text;
                        else if (value != null)
                            cache[key] = value;
                    }
                }
            }
            return;
        }
    }

    #endregion

    #region Convenience

    static String IntoQuotedJSONString(Object obj)
    {
        String text = obj == null ? "" : obj.ToString();
        StringBuilder sb = new StringBuilder(text.Length + 2);
        sb.Append('"');
        foreach (char c in text)
        {
            if (c == '"')
                sb.Append("\\\"");  // escape the essential 
            else if (c == '\\')
                sb.Append("\\\\");
            else if (c == '\n')     // ...and line control related
                sb.Append("\\n");
            else if (c == '\r')
                sb.Append("\\r");
            else
                sb.Append(c);
        }
        return sb.Append('"').ToString();
    }

    #endregion

}
