from pdb import set_trace
from URAnalysis.PlotTools.Plotter import Plotter
import URAnalysis.PlotTools.views as urviews
import os, glob, sys, logging, ROOT, rootpy
from URAnalysis.Utilities.datacard import DataCard
from URAnalysis.Utilities.roottools import slice_hist
from styles import styles
import rootpy.plotting as plotting
views = plotting.views
import rootpy.io as io
from array import array
from pdb import set_trace
from fnmatch import fnmatch
import URAnalysis.Utilities.prettyjson as prettyjson
import URAnalysis.Utilities.quad as quad
rootpy.log["/"].setLevel(rootpy.log.INFO)
ROOT.gStyle.SetOptTitle(0)
ROOT.gStyle.SetOptStat(0)
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument('--noplots', dest='noplots', action='store_true',
                    help='skip plot making')
parser.add_argument('--noshapes', dest='noshapes', action='store_true',
                    help='skip shape making')
opts = parser.parse_args()

class TTXSecPlotter(Plotter):
   def __init__(self):
      jobid = os.environ['jobid']
      files = glob.glob('results/%s/ttbarxsec/*.root' % jobid)
      if len(files) == 0:
         logging.info('No file found, must be Otto\'s format...')
         all_files = glob.glob('results/%s/ttbarxsec/*/*.root' % jobid)
         files = {}
         for ifile in all_files:
            base = os.path.basename(ifile)
            if base not in files: 
               files[os.path.basename(ifile)] = []
            files[os.path.basename(ifile)].append(
               (os.path.basename(os.path.dirname(ifile)), io.root_open(ifile))
               )
         files = dict((i, urviews.MultifileView(*j)) for i, j in files.iteritems())

      logging.debug('files found %s' % files.__repr__())
      lumis = glob.glob('inputs/%s/*.lumi' % jobid)
      logging.debug('lumi files found %s' % lumis.__repr__())
      
      outdir= 'plots/%s/ttxsec' % jobid
      super(TTXSecPlotter, self).__init__(
         files, lumis, outdir, styles, None, 10000
         )
      self.jobid = jobid

      self.views['ttJets_rightAssign'] = {
         'view' : self.create_tt_subsample(
            'semilep_visible_right', 
            'tt, right cmb',
            '#6666b3'
            )
         }
      self.views['ttJets_rightThad'] = {
         'view' : self.create_tt_subsample(
            'semilep_right_thad', 
            'tt, right t_{h}',
            ),
         }
      self.views['ttJets_rightTlep'] = {
         'view' : self.create_tt_subsample(
            'semilep_right_tlep', 
            'tt, right t_{l}',
            '#cccce6'
            )
         }
      self.views['ttJets_wrongAssign'] = {
         'view' : self.create_tt_subsample(
            'semilep_wrong', 
            'tt, wrong cmb',
            '#88a7c4'
            )
         }
      self.views['ttJets_other'] = {
         'view' : self.create_tt_subsample(
            'other_tt_decay', 
            'Other tt decay',
            '#668db3',
            )
         }

      for sample in self.views:
         if not sample.startswith('ttJets'):
            self.views[sample]['view'] = views.SubdirectoryView(self.views[sample]['view'], 'RECO')

      self.mc_samples = [
         '[WZ]Jets',
         'single*',
         'ttJets_rightAssign',
         'ttJets_rightThad',
         'ttJets_rightTlep',
         'ttJets_wrongAssign',
         'ttJets_other'
         ]

      self.card_names = [
         'vjets',
         'single_top',
         'tt_right',
         'tt_right_th',
         'tt_right_tl',
         'tt_wrong',
         'tt_other'
         ]

      self.systematics = {
         'lumi' : {
            'type' : 'lnN',
            'samples' : ['*'],
            'categories' : ['*'],
            'value' : 1.05,
            },
         'JES' : {
            'samples' : ['*'],
            'categories' : ['*'],
            'type' : 'shape',
            '+' : lambda x: x.replace('nosys', 'jes_up'),
            '-' : lambda x: x.replace('nosys', 'jes_down'),
            }
         }
      self.card = None

   def create_tt_subsample(self, subdir, title, color='#9999CC'):
      return views.StyleView(
         views.TitleView(
            views.SubdirectoryView(
               self.views['ttJets_pu30']['view'],
               subdir
               ),
            title
            ),
         fillcolor = color,
         linecolor = color
         )

   def save_card(self, name):
      if not self.card:
         raise RuntimeError('There is no card to save!')
      self.card.save(name, self.outputdir)
      self.card = None

   def add_systematics(self):
      pass

   def write_shapes(self, folder, variable, xbinning, ybinning, 
                    category_template='Bin%i', slice_along='X'):
      if not self.card: self.card = DataCard('tt_right')
      #keep it there for systematics
      mc_views = dict(
            (name, view) for name, view in zip(
               self.card_names,
               self.mc_views(rebin=[xbinning, ybinning])
               )
            )

      path = os.path.join(folder, variable)
      mc_hists2D = dict(
         (name, view.Get(path)) for name, view in mc_views.iteritems()
         )

      category_axis = 'GetNbinsX' if slice_along == 'Y' else 'GetNbinsY'
      nbins = getattr(mc_hists2D.values()[0], category_axis)()
      fake_data = sum(i for i in mc_hists2D.values())

      for idx in range(1, nbins+1):
         self.card.add_category(category_template % idx)
         category = self.card[category_template % idx]
         for name, hist in mc_hists2D.iteritems():
            category[name] = slice_hist(hist, idx+1, axis=slice_along)
         category['data_obs'] = slice_hist(fake_data, idx+1, axis=slice_along)
         integral = category['data_obs'].Integral()
         if integral != 0:
            int_int = float(int(integral))
            category['data_obs'].Scale(int_int/integral)

plotter = TTXSecPlotter()

##################
#     PLOTS
##################
if not opts.noplots:
   to_plot = [
      ('all_lep_pt')  ,
      ('all_tlep_eta'),
      ('all_thad_pt') ,
      ('all_tlep_pt') ,
      ('all_thad_eta'),
      ("all_ttm" ),
      ("all_tty" ),
      ("all_ttpt"),
      ("all_costhetastar"),
      ("all_njet"),
      ]

   for var in to_plot:
      plotter.plot_mc_vs_data('', var, leftside=False, rebin=4)
      plotter.save(var, pdf=False)

   plotter.plot_mc_vs_data(
      '', 'all_fullDiscr_ptthad', leftside=False, 
      preprocess=lambda x: urviews.ProjectionView(x, 'X', [-10, 10])
      )
   plotter.save('fullDiscr', pdf=False)
##################
#     CARDS
##################
if not opts.noshapes:
   pt_binning = [40., 75., 105., 135., 170., 220., 300., 1000.]
   ## eta_binning = [0., 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.3, 2.8, 8.0]
   ## mass_binning = [250., 350., 370., 390., 410., 430., 450., 470., 490., 510., 530., 550., 575., 600., 630., 670., 720., 800., 900, 5000.]
   ## y_binning = [0., 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 3.]
   ## ttpt_binning = [0., 20., 30., 40., 50., 60., 70., 90., 110., 140., 180., 250., 1000.]

   full_discr_binning = range(-10, 12, 2) 
   to_fit = [
      ("ptthad"	, pt_binning),
      ("pttlep"	, pt_binning),
   ##    ("etathad", eta_binning),
   ##    ("etatlep", eta_binning),
   ##    ("ttm"		, mass_binning),
   ##    ("tty"		, y_binning),
   ##    ("ttpt"   , ttpt_binning),
      ]
   discriminant = 'fullDiscr'
   
   for var, binning in to_fit:
      plotter.write_shapes(
         '', 'all_%s_%s' % (discriminant, var), full_discr_binning, binning
         ) 
      plotter.card.add_systematic('lumi', 'lnN', '*', '*', 1.05)
      #plotter.card.add_bbb_systematics(['*'], ['*'])
      plotter.save_card(var)
