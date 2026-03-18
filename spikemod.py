

import wx
import random
import numpy as np

from HypoModPy.hypomods import *
from HypoModPy.hypoparams import *
from HypoModPy.hypodat import *
from HypoModPy.hypogrid import *
from HypoModPy.hypospikes import *

from spikepanels import SpikeModBox, SecModBox


class SpikeMod(Mod):
    def __init__(self, mainwin, tag):
        Mod.__init__(self, mainwin, tag)

        if mainwin.modpath != "": self.path = mainwin.modpath + "/Spike"
        else: self.path = "Spike"

        if os.path.exists(self.path) == False: 
            os.mkdir(self.path)

        self.mainwin = mainwin

        # tool boxes
        self.gridbox = GridBox(self, "Data Grid", wx.Point(0, 0), wx.Size(320, 500), 100, 20)
        self.gridbox.NeuroButton()
        self.secmodbox = SecModBox(self, "secmod", "Secretion Model", wx.Point(0, 0), wx.Size(320, 500))
        self.spikemodbox = SpikeModBox(self, "spikemod", "Spike Model", wx.Point(0, 0), wx.Size(320, 500))
        self.spikedatabox = SpikeDataBox(self, "spikedatabox", "Spike Data", wx.Point(0, 0), wx.Size(320, 500))

        # link mod owned boxes
        mainwin.gridbox = self.gridbox
        mainwin.spikedatabox = self.spikedatabox

        # spike data analysis stores
        self.cellspike = SpikeDat()
        self.modspike = SpikeDat()

        # spike data stores
        self.spikedata = []

        self.AddTool(self.spikemodbox)
        self.AddTool(self.secmodbox)
        self.AddTool(self.gridbox)
        self.AddTool(self.spikedatabox)
    
        self.spikemodbox.Show(True)
        self.modbox = self.spikemodbox

        self.ModLoad()
        print("Spike Model OK")

        self.PlotData()
        self.graphload = True


    ## PlotData() defines all the available plots, each linked to a data array in osmodata
    ##
    def PlotData(self):
        # Data plots
        #
        # AddPlot(PlotDat(data array, xfrom, xto, yfrom, yto, label string, plot type, bin size, colour), tag string)
        # ----------------------------------------------------------------------------------
        self.plotbase.AddPlot(PlotDat(self.cellspike.hist5, 0, 2000, 0, 500, "Cell Hist 5ms", "line", 1, "blue"), "datahist5")
        self.plotbase.AddPlot(PlotDat(self.cellspike.hist5norm, 0, 2000, 0, 500, "Cell Hist 5ms Norm", "line", 1, "blue"), "datahist5norm")
        self.plotbase.AddPlot(PlotDat(self.cellspike.haz5, 0, 2000, 0, 100, "Cell Haz 5ms", "line", 1, "blue"), "datahaz5")
        self.plotbase.AddPlot(PlotDat(self.modspike.hist5, 0, 2000, 0, 100, "Mod Hist 5ms", "line", 1, "green"), "modhist5")
        self.plotbase.AddPlot(PlotDat(self.modspike.hist5norm, 0, 2000, 0, 100, "Mod Hist 5ms Norm", "line", 1, "green"), "modhist5norm")
        self.plotbase.AddPlot(PlotDat(self.modspike.haz5, 0, 2000, 0, 100, "Mod Haz 5ms", "line", 1, "green"), "modhaz5")

        self.plotbase.AddPlot(PlotDat(self.cellspike.srate1s, 0, 500, 0, 20, "Cell Spike Rate 1s", "spikes", 1, "red"), "cellrate1s")
        self.plotbase.AddPlot(PlotDat(self.modspike.srate1s, 0, 500, 0, 20, "Mod Spike Rate 1s", "spikes", 1, "purple"), "modrate1s")

        self.IoDGraph(self.cellspike.IoDdata, self.cellspike.IoDdataX, "IoD Cell", "iodcell", "lightblue", 10)
        self.IoDGraph(self.modspike.IoDdata, self.modspike.IoDdataX, "IoD Mod", "iodmod", "lightgreen", 0)



    def DefaultPlots(self):
        if len(self.mainwin.panelset) > 0: self.mainwin.panelset[0].settag = "datahist5"
        if len(self.mainwin.panelset) > 1: self.mainwin.panelset[1].settag = "datahaz5"
        if len(self.mainwin.panelset) > 2: self.mainwin.panelset[2].settag = "modhist5"


    def NeuroData(self):
        DiagWrite("NeuroData() call\n")

        self.cellindex = self.spikedatabox.cellpanel.cellindex
        self.cellspike.Analysis(self.spikedata[self.cellindex])
        self.cellspike.id = self.cellindex
        self.cellspike.name = self.spikedata[self.cellindex].name
        self.spikedatabox.cellpanel.PanelData(self.cellspike)

        self.mainwin.scalebox.GraphUpdateAll()


    def ModelData(self):
        DiagWrite("ModelData() call\n")

        self.modspike.Analysis()
        self.spikemodbox.SpikeData(self.modspike)
        self.mainwin.scalebox.GraphUpdateAll()


    def OnModThreadComplete(self, event):
        self.mainwin.scalebox.GraphUpdateAll()
        DiagWrite(f"Model thread OK, test value {event.GetInt()}\n\n")
        self.runflag = False
        self.ModelData()


    def OnModThreadProgress(self, event):
        self.spikemodbox.SetCount(event.GetInt())
        #DiagWrite(f"Model thread progress, value {event.GetInt()}\n\n")


    def RunModel(self):
        if not self.runflag:
            self.mainwin.SetStatusText("Spike Model Run")
            self.runflag = True
            params = {
                "spike": self.modbox.GetParams(),
                "sec": self.secmodbox.GetParams()
            }

            # multibox example
            #
            # params = {
            #     "spike": self.spikebox.GetParams(),
            #     "neuro": self.neurobox.GetParams(),
            #     "syn": self.synbox.GetParams(),
            # }
            #

            modthread = SpikeModel(self, params)
            modthread.start()
           


class SpikeModel(ModThread):
    def __init__(self, mod, params):
        ModThread.__init__(self, params, mod.mainwin)

        self.params = params
        self.mod = mod
        self.spikemodbox = mod.spikemodbox
        self.mainwin = mod.mainwin
        self.scalebox = mod.mainwin.scalebox


    # run() is the thread entry function, used to initialise and call the main Model() function   
    def run(self):
        # Read model flags
        self.randomflag = self.spikemodbox.modflags["randomflag"]      # model flags are useful for switching elements of the model code while running

        if self.randomflag: random.seed(0)
        else: random.seed(datetime.now().microsecond)

        DiagWrite("Running Spike Model\n")

        self.Model()
        completeevent = ModThreadEvent(ModThreadCompleteEvent)
        wx.QueueEvent(self.mod, completeevent)


    # Model() reads in the model parameters, initialises variables, and runs the main model loop
    def Model(self):
        spikedata = self.mod.modspike
        spikeparams = self.params["spike"]
        secparams = self.params["sec"]

        # Read parameters
        runtime = int(spikeparams["runtime"])
        hstep = spikeparams["hstep"]
        Vthresh = spikeparams["Vthresh"]
        Vrest = spikeparams["Vrest"]
        pspmag = spikeparams["pspmag"]
        psprate = spikeparams["psprate"]
        pspratio = spikeparams["pspratio"]
        halflifeMem = spikeparams["halflifeMem"]
        kHAP = spikeparams["kHAP"]
        halflifeHAP = spikeparams["halflifeHAP"]
        kAHP = spikeparams["kAHP"]
        halflifeAHP = spikeparams["halflifeAHP"]

        halflifeB = secparams["halflifeB"]
        halflifeE = secparams["halflifeE"]
        halflifeC = secparams["halflifeC"]
        Ethresh = secparams["Eth"]
        Cthresh = secparams["Cth"]
        Bbase = secparams["Bbase"]
        alpha = secparams["alpha"]
        Pmax = secparams["Pmax"]
        Rinit = secparams["Rinit"]
        secExp = secparams["secExp"]
        beta = secparams["beta"]
        Rmax = secparams["Rmax"]
        kB = secparams["kB"]
        kE = secparams["kE"]
        kC = secparams["kC"]

        epspmag = pspmag
        ipspmag = pspmag
        absref = 2
        

        # Time Constants - conversion from half-life

        # Spiking 
        tauMem = math.log(2) / halflifeMem
        tauHAP = math.log(2) / halflifeHAP
        tauAHP = math.log(2) / halflifeAHP

        # Secretion
        tauB = math.log(2) / halflifeB
        tauE = math.log(2) / halflifeE
        tauC = math.log(2) / halflifeC
        tauDiff = math.log(2) / secparams["halflifeDiff"]
        tauClear = math.log(2) / secparams["halflifeClear"]



        # Initialise variables
        epsprate = 0
        ipsprate = 0
        epspt = 0
        ipspt = 0
        ttime = 0
        V = Vrest
        inputPSP = 0
        tPSP = 0
        tHAP = 0
        tAHP = 0

        tB = 0  # Broadening
        tE = 0  # Fast Ca2+
        tC = 0.03   # Slow Ca2+
        tR = Rinit  # Reserve Pool
        tP = Pmax   # Releasable Pool 
        tPlasma = 0 # Hormone plasma concentration
        tEVF = 0

        Ethpow = Ethresh * Ethresh * Ethresh * Ethresh * Ethresh  # precalculate instead of each loop
        Cthpow = Cthresh * Cthresh * Cthresh

        spikedata.spikecount = 0
        maxspikes = spikedata.maxspikes
        neurotime = 0
        runtime = runtime * 1000

        # Run model loop
        for i in range(1, runtime + 1):
            ttime += 1
            neurotime += 1
            if i%(runtime/100) == 0: 
                progevent = ModThreadEvent(ModThreadProgressEvent)
                progevent.SetInt(math.floor(neurotime / runtime * 100)) 
                wx.QueueEvent(self.mod, progevent)                        # Update run progress % in model panel

            # PSP input signal
            nepsp = 0
            nipsp = 0
            epsprate = psprate / 1000
            ipsprate = epsprate * pspratio

            if epsprate > 0: 
                while epspt < hstep:
                    erand = random.random()
                    nepsp += 1
                    epspt = -math.log(1 - erand) / epsprate + epspt
                epspt = epspt - hstep

            if ipsprate > 0: 
                while ipspt < hstep:
                    irand = random.random()
                    nipsp += 1
                    ipspt = -math.log(1 - irand) / ipsprate + ipspt
                ipspt = ipspt - hstep

            inputPSP = nepsp * epspmag - nipsp * ipspmag


            # Spiking Model
            tPSP = tPSP + inputPSP - tPSP * tauMem
            tHAP = tHAP - tHAP * tauHAP
            tAHP = tAHP - tAHP * tauAHP
            V = Vrest + tPSP - tHAP - tAHP

            #print(f"SpikeModel step {i}  V {V:.2f}  tPSP {tPSP:.2f}  inputPSP {inputPSP:.2f}  nepsp {nepsp}")


            # Secretion Model
            tB = tB - (tB * tauB)    # broadening
            tE = tE - (tE * tauE)    # fast Ca2+
            tC = tC - (tC * tauC)    # slow Ca2+

            EKpow = tE * tE * tE * tE * tE
            Einh = 1 - EKpow / (EKpow + Ethpow)
            CKpow = tC * tC * tC
            Cinh = 1 - CKpow / (CKpow + Cthpow) 
            CaEnt = Einh * Cinh * (tB + Bbase)   # Ca Entry
            if secExp == 3: tEpow = tE * tE * tE            # vaso
            if secExp == 2: tEpow = tE * tE                 # oxy
            secX = tEpow * alpha * tP       # secretion rate, proportional to releasable pool and fast Ca2+

            # Reserve Store (tR) and Releasable Pool (tP)
            if tP < Pmax: 
                fillP = beta * tR / Rmax
            else:
                fillP = 0

            tP = tP - secX + fillP     # Releasable pool is decremented by secretion, incremented by filling from reserve store
            fillR = 0   # no synthesis in this version
            tR = tR + fillR - fillP    # Reserve store is decremented by filling releasable pool, incremented by synthesis

            # Plasma Model
            tPlasma = tPlasma + secX - tPlasma * tauClear
            #tEVF = tEVF + tPlasma * tauDiff - tEVF


            # Spiking
            if V > Vthresh and ttime >= absref:

                # record spike time
                if spikedata.spikecount < maxspikes: 
                    spikedata.times[spikedata.spikecount] = neurotime
                    spikedata.spikecount += 1
    
                # Spike incremented variable
                # afterpotentials
                tHAP = tHAP + kHAP
                tAHP = tAHP + kAHP

                tB = tB + kB
                tE = tE + kE * CaEnt
                tC = tC + kC * CaEnt	
                
                ttime = 0   # reset time since last spike

        # Finalise data
        freq = spikedata.spikecount / (runtime / 1000)
        DiagWrite(f"Spike Model OK, generated {spikedata.spikecount} spikes, freq {freq:.2f}\n")



    



