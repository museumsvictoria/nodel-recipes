using System;
using System.Threading.Tasks;
using System.Runtime.InteropServices;

[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume
{
    // f(), g(), ... are unused COM method slots.
    int f(); int g(); int h(); int i();
    int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
    int j();
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int k(); int l(); int m(); int n();
    int SetMute([MarshalAs(UnmanagedType.Bool)] bool bMute, System.Guid pguidEventContext);
    int GetMute(out bool pbMute);
}

[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice
{
    int Activate(ref System.Guid id, int clsCtx, int activationParams, out IAudioEndpointVolume aev);
}

[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator
{
    int f(); // Unused
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint);
}

[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumeratorComObject { }

// https://community.idera.com/database-tools/powershell/powertips/b/tips/posts/controlling-audio-volume-and-mute-status
public class AudioEndpoint
{
    static IAudioEndpointVolume Vol()
    {
        var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev = null;
        Marshal.ThrowExceptionForHR(enumerator.GetDefaultAudioEndpoint(/*eRender*/ 0, /*eMultimedia*/ 1, out dev));
        IAudioEndpointVolume epv = null;
        var epvid = typeof(IAudioEndpointVolume).GUID;
        Marshal.ThrowExceptionForHR(dev.Activate(ref epvid, /*CLSCTX_ALL*/ 23, 0, out epv));
        return epv;
    }
    public static float Volume
    {
        get { float v = -1; Marshal.ThrowExceptionForHR(Vol().GetMasterVolumeLevelScalar(out v)); return v; }
        set { Marshal.ThrowExceptionForHR(Vol().SetMasterVolumeLevelScalar(value, System.Guid.Empty)); }
    }
    public static bool Mute
    {
        get { bool mute; Marshal.ThrowExceptionForHR(Vol().GetMute(out mute)); return mute; }
        set { Marshal.ThrowExceptionForHR(Vol().SetMute(value, System.Guid.Empty)); }
    }
}

class VolumeController
{
    static bool current_mute_status = AudioEndpoint.Mute;
    static float current_volume_status = AudioEndpoint.Volume;
    static bool running = true;

    static void Main(string[] args)
    {
        Console.OutputEncoding = System.Text.Encoding.UTF8;
        Console.ForegroundColor = ConsoleColor.Blue;
        Console.WriteLine("ʕ•ᴥ•ʔ");
        Console.ResetColor();
        Console.WriteLine("Volume Controller started!");

        AppDomain.CurrentDomain.ProcessExit += new EventHandler(CurrentDomain_ProcessExit);

        // Monitor and announces changes to system volume.
        MonitorSystemVolume();

        // Monitor stdin for commands.
        MonitorUserInput();
    }

    static void CurrentDomain_ProcessExit(object sender, EventArgs e)
    {
        running = false;
        Console.WriteLine("Volume Controller exited!");
    }

    static async void MonitorSystemVolume()
    {
        // Console.WriteLine("- Started monitoring system volume.");
        while (running)
        {
            // Compare previous and current (from endpoint) mute status updating if neccesary.
            if (current_mute_status != AudioEndpoint.Mute)
            {
                current_mute_status = AudioEndpoint.Mute;
                AnnounceMuteStatus();
            }
            // Compare previous and current (from endpoint) volume status updating if neccesary.
            if (current_volume_status != AudioEndpoint.Volume)
            {
                current_volume_status = AudioEndpoint.Volume;
                AnnounceVolumeStatus();
            }

            await Task.Delay(250);
        }
    }

    static void PrintValidInputs()
    {
        Console.WriteLine("-- get-mute");
        Console.WriteLine("-- set-mute (0 or 1)");
        Console.WriteLine("-- get-volume");
        Console.WriteLine("-- set-volume (0 - 100)");
        Console.WriteLine("-- q");
    }

    static async void MonitorUserInput()
    {
        // Console.WriteLine("- Started monitoring user input.");

        while (running)
        {
            Task<string> task = Console.In.ReadLineAsync();
            String line = await task;

            if (line.Equals("get-mute"))
            {
                AnnounceMuteStatus();
            }
            else if (line.Equals("set-mute 1"))
            {
                AudioEndpoint.Mute = true;
            }
            else if (line.Equals("set-mute 0"))
            {
                AudioEndpoint.Mute = false;
            }
            else if (line.Equals("get-volume"))
            {
                AnnounceVolumeStatus();
            }
            else if (line.Split(' ')[0].Equals("set-volume"))
            {
                AudioEndpoint.Volume = float.Parse(line.Split(' ')[1]) / 100;
            }
            else if (line.Equals("q"))
            {
                Console.WriteLine("Goodbye!");
                return;
            }
            else
            {
                PrintValidInputs();
            }
        }

    }

    static void AnnounceMuteStatus()
    {
        Console.WriteLine("{'event': 'MuteStatus', 'arg': " + AudioEndpoint.Mute + "}");
    }

    static void AnnounceVolumeStatus()
    {
        Console.WriteLine("{'event': 'VolumeStatus', 'arg': " + Math.Round(AudioEndpoint.Volume * 100) + "}");
    }
}
