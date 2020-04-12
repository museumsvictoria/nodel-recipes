using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

// This program measures CPU level

namespace ConsoleApplication1
{
    class Program
    {
        static void Main(string[] args)
        {
            query();
        }

        static void query()
        {
            PerformanceCounter cpuCounter = new PerformanceCounter();
            cpuCounter.CategoryName = "Processor";
            cpuCounter.CounterName = "% Processor Time";
            cpuCounter.InstanceName = "_Total";

            // Get Current Cpu Usage
            var baseSnap = cpuCounter.NextSample();

            var currentCpuUsage = cpuCounter.NextValue();

            for(;;)
            {
                Thread.Sleep(10000);
                var currentSnap = cpuCounter.NextSample();

                var diff = currentSnap.RawValue - baseSnap.RawValue;

                currentCpuUsage = cpuCounter.NextValue();
                // log("CPU:" + currentCpuUsage + ", diff:" + diff + ", ave:" + diff/4);
                Console.WriteLine("{'event': 'CPU', 'arg': " + currentCpuUsage + "}");
            }

        }

    }
}