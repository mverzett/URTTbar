from pdb import set_trace
from URAnalysis.PlotTools.Plotter import Plotter
import URAnalysis.PlotTools.views as urviews
import os, glob, sys, logging, ROOT, rootpy, itertools
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
ROOT.gROOT.SetBatch(True)
from argparse import ArgumentParser
from URAnalysis.Utilities.struct import Struct
import re
from TTXSecPlotter import TTXSecPlotter
from array import array

def run_module(**kwargs):
   ##################
   #  DEFINITIONS
   ##################
   opts = Struct(**kwargs)
   #when running optimization we do not want to
   #plot anything!
   if opts.optimize_binning and len(opts.optimize_binning):
      opts.noplots = True
   if opts.binning and len(opts.binning):
      opts.noplots = True

   discriminant =  'massDiscr'
   phase_space = 'fiducialtight'
   full_discr_binning = [2]#range(-15, 16)

   jet_categories = [
      ('0Jets', ['0']), 
      ('1Jets', ['1']), 
      ('2Jets', ['2', '3']), 
   ##    ('3Jets', ['3']), 
      ]
   ## jet_categories = [ 
   ##    ('0Jets', ['0', '1', '2', '3'])
   ##    ]
      
   ## mass_binning = [250., 350., 370., 390., 410., 430., 450., 470., 490., 510., 530., 550., 575., 600., 630., 670., 720., 800., 900, 5000.]
   ## y_binning = [0., 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 3.]
   ## ttpt_binning = [0., 20., 30., 40., 50., 60., 70., 90., 110., 140., 180., 250., 1000.]

   def flat_bin(width, strt, stop): 
      ret = []
      val = strt
      while val <= stop:
         ret.append(val)
         val += width
      return ret

   vars_to_unfold = [
      Struct(
         var = 'thadpt',
         binning = Struct(
            gen  = flat_bin(40, 0, 500),#[0., 45., 105., 165., 225., 285., 800.],
            reco = flat_bin(40, 0, 500),#[20.0*i for i in range(11)]+[800.],
            ),
         xtitle  = 'p_{T}(t_{had}) [GeV]'
         ),
      Struct(
         var = 'tleppt',
         binning = Struct(
            gen  = flat_bin(40, 0, 500),#[0., 60., 120., 180., 240., 300., 800.],
            reco = flat_bin(40, 0, 500),#[20.0*i for i in range(11)]+[800.],
            ),
         xtitle = 'p_{T}(t_{lep}) [GeV]'
         ),
      Struct( 
         var = 'tlepy',
         #other_name = 'tleppt',
         binning = Struct(
            gen  = flat_bin(0.2, 0, 2.5),#
            reco = flat_bin(0.2, 0, 2.5),#
            ),
         xtitle = '|y(t_{lep})|'
         ),
      Struct( 
         var = 'thady',
         binning = Struct(
            gen  = flat_bin(0.2, 0, 2.5),#
            reco = flat_bin(0.2, 0, 2.5),#
            ),
         xtitle = '|y(t_{had})|'
         ),
      Struct( 
         var = 'tty',
         binning = Struct(
            gen  = flat_bin(0.2, 0, 2.5),#
            reco = flat_bin(0.2, 0, 2.5),#
            ),
         xtitle = '|y(tt)|'
         ),
      Struct(
         var = 'ttpt',
         binning = Struct(
            gen = flat_bin(20, 0, 500),#[0., 45., 105., 165., 225., 285., 800.],
            reco = flat_bin(20, 0, 500),#[20.0*i for i in range(11)]+[800.],
            ),
         xtitle  = 'p_{T}(tt) [GeV]'
         ),
      Struct(
         var = 'ttM',
         binning = Struct(
            gen  = flat_bin(100, 250, 1450),
            reco = flat_bin(100, 250, 1450),
            ),
         xtitle  = 'M(tt) [GeV]'
         ),
   ]

   dir_postfix = ''
   if opts.optimize_binning and len(opts.optimize_binning):
      varname, prev, startbin, binning = tuple(opts.optimize_binning.split(':'))
      if not any(i.var == varname for i in vars_to_unfold):
         raise ValueError('Sample %s is not among the ones I have to unfold!' % sample)
      binning = eval(binning)
      prev = eval(prev)
      startbin = float(startbin)
      info = [i for i in vars_to_unfold if i.var == varname][0]
      #use ONLY the variable we want
      vars_to_unfold = []
      for stop in binning:
         clone = info.clone()
         clone.binning.reco = prev + [startbin, stop]
         clone.dir_postfix = '_'.join(['%.1f' % i for i in clone.binning.reco])
         vars_to_unfold.append( clone )

   if opts.binning and len(opts.binning):
      varname, binning = tuple(opts.binning.split(':'))
      if not any(i.var == varname for i in vars_to_unfold):
         raise ValueError('Sample %s is not among the ones I have to unfold!' % sample)
      binning = eval(binning)
      info = [i for i in vars_to_unfold if i.var == varname][0]
      info.binning.reco = binning
      info.dir_postfix = '_'.join(['%.1f' % i for i in info.binning.reco])
      #use ONLY the variable we want
      vars_to_unfold = [
         info
         ]

   flumi = None if opts.lumi == -1. else opts.lumi
   plotter = TTXSecPlotter(lumi=flumi)
   if opts.nodata:
      del plotter.views['data']
   
   plotter.views['ttJets_rightAssign'] = {
      'view' : plotter.create_tt_subsample(
         ['semilep_visible_right'], 
         'tt, right cmb',
         '#5555ab'
         )
      }
   plotter.views['ttJets_rightThad'] = {
      'view' : plotter.create_tt_subsample(
         ['semilep_right_thad'], 
         'tt, right t_{h}',
         '#aaaad5'
         ),
      }
   plotter.views['ttJets_rightTlep'] = {
      'view' : plotter.create_tt_subsample(
         ['semilep_right_tlep'], 
         'tt, right t_{l}',
         '#ab5555'
         )
      }
   plotter.views['ttJets_wrongAssign'] = {
      'view' : plotter.create_tt_subsample(
         ['semilep_wrong'], 
         'tt, wrong cmb',
         '#d5aaaa'
         )
      }
   plotter.views['ttJets_other'] = {
      'view' : plotter.create_tt_subsample(
         ['other_tt_decay'], 
         'Other tt decay',
         '#668db3',
         )
      }
   plotter.views['ttJets_wrong'] = {
      'view' : urviews.MultifileView(
         **{'' : plotter.create_tt_subsample(
               ['semilep_wrong', 
                'other_tt_decay',
                'semilep_right_tlep',],
               'tt, wrong cmb',
               '#ab5555'
               ),
            'otherTT_ratio_up' : plotter.create_tt_subsample(
               ['semilep_wrong', 
                'other_tt_decay',
                'semilep_right_tlep',],
               'tt, wrong cmb',
               '#ab5555',
               relative_scale=[1., 1.5, 1.]
               ),
            'otherTT_ratio_down' : plotter.create_tt_subsample(
               ['semilep_wrong', 
                'other_tt_decay',
                'semilep_right_tlep',],
               'tt, wrong cmb',
               '#ab5555',
               relative_scale=[1., 0.5, 1.]
               )
            }
         )
      }
               
   plotter.mc_samples = [
      'QCD*',
      '[WZ]Jets',
      'single*',
      
      'ttJets_rightThad',
      'ttJets_rightTlep',
      'ttJets_wrongAssign',
      #'ttJets_wrong',
      'ttJets_other',
      'ttJets_rightAssign',
      ]

   plotter.card_names = {
      'vjets' : ['[WZ]Jets'],
      'single_top' : ['single*'],
      'tt_right' : ['ttJets_rightAssign'],
      'tt_wrong' : ['ttJets_wrong'],
      #'tt_other' : ['ttJets_other'],
      'only_thad_right' : ['ttJets_rightThad'],
      'qcd' : ['QCD*'],
      }

   plotter.systematics = {
      'lumi' : {
         'type' : 'lnN',
         'samples' : ['(?!tt_).*'],
         'categories' : ['.*'],
         'value' : 1.05,
         },

      ## 'otherTT_ratio' : {
      ##    'type' : 'shape',
      ##    'samples' : ['tt_wrong'],
      ##    'categories' : ['.*'],
      ##    '+' : lambda x: 'otherTT_ratio_up/%s' % x,
      ##    '-' : lambda x: 'otherTT_ratio_down/%s' % x,
      ##    'value' : 1.00,
      ##    'shape_only' : True,
      ##    },

      ## 'JES' : {
      ##    'samples' : ['*'],
      ##    'categories' : ['*'],
      ##    'type' : 'shape',
      ##    '+' : lambda x: x.replace('nosys', 'jes_up'),
      ##    '-' : lambda x: x.replace('nosys', 'jes_down'),
      ##    'value' : 1.00,
      ##    },

      'MCStat' : {
         'samples' : ['only_thad_right'],
         'categories' : ['.*'],
         'type' : 'stat',
         'multiplier' : 4.,
         }
      }


   ##################
   #     PLOTS
   ##################
   if not opts.noplots:

      #cut flow
      plotter.cut_flow()
      plotter.save('cut_flow')

      #rate evolution
      plotter.initviews()
      lumi = plotter.views['data']['intlumi']
      MC_sum = sum(plotter.make_stack(folder='electrons/nosys').Get('byrun').hists)
      electrons_expectation = MC_sum[0].value/lumi
      print electrons_expectation
      plotter.plot('data', 'electrons/nosys/byrun')
      ref_function = ROOT.TF1('f', "%s" % electrons_expectation, 0., 12.)
      ref_function.SetLineWidth(3)
      ref_function.SetLineStyle(2)
      ref_function.Draw('same')      
      plotter.save('run_evolution_electrons', pdf=False)


      MC_sum = sum(plotter.make_stack(folder='muons/nosys').Get('byrun').hists)
      muons_expectation = MC_sum[0].value/lumi
      plotter.plot('data', 'muons/nosys/byrun')
      ref_function = ROOT.TF1('f', "%s" % muons_expectation, 0., 12.)
      ref_function.SetLineWidth(3)
      ref_function.SetLineStyle(2)
      ref_function.Draw('same')      
      plotter.save('run_evolution_muons', pdf=False)

      plotter.merge_leptons(['muons'])
      to_plot = [
         ('weight' , 5, 'event weight', {'postprocess' : lambda x: urviews.OverflowView(x)}),
         ('nvtx' , 2, '# vertices', {}),
         ('rho' , 5, '#rho', {}),
         ('lep_pt' , 10, 'p_{T}(l) [GeV]', {}),
         ('lepp_eta' , 8, '#eta(l+)', {}),
         ('lepm_eta' , 8, '#eta(l-)', {}),
         ('bjet_pt'  , 4, 'p_{T}(b) [GeV]', {}),
         ('wjet_pt'  , 4, 'p_{T}(wj) [GeV]', {}),
         ('bjet_eta' , 4, '#eta(b)', {}),
         ('wjet_eta' , 4, '#eta(wj)', {}),
         ('thadmass' ,10, 'M(t_{had})', {'leftside' : True}),
         ('whadmass' ,10, 'M(W_{had})', {}),
         ('Mt_W', 10, 'M_{T}(#ell, MET)', {}),
         ## ("ttM"    ,20, 'm(t#bar{t})', {}),
         ## ("tty"    , 4, 'y(t#bar{t})', {}),
         ## ("ttpt"   , 5, 'p_{T}(t#bar{t})', {}),
         ("costhetastar", 4, '', {}),
         ("njets", 3, '# of jets', {}),
         (discriminant, 2, 'discriminant', {}),
         ]

      plotter.plot_mc_shapes(
         'nosys', discriminant, rebin=2, xaxis=discriminant,
         leftside=False, normalize=True, show_err=True, xrange=(-8,1))
      plotter.save('%s_full_shape' % (discriminant), pdf=False)
      
      plotter.plot_mc_shapes(
         'nosys', discriminant, rebin=2, xaxis=discriminant,
         leftside=False, normalize=True, show_err=True, xrange=(-8,1),
         use_only=set(['ttJets_rightTlep', 'ttJets_wrongAssign', 'ttJets_other']),
         ratio_range=1)
      plotter.save('%s_bkg_shape' % (discriminant), pdf=False)

      for var, rebin, xaxis, kwargs in to_plot:
         leftside=kwargs.get('leftside', False)
         if 'leftside' in kwargs:
            del kwargs['leftside']
         plotter.plot_mc_vs_data(
            'nosys', var, leftside=leftside, rebin=rebin, xaxis=xaxis, show_ratio=True,
            ratio_range=0.5, **kwargs)
         #set_trace()
         #plotter.reset(); plotter.plot_mc_vs_data('nosys', var, leftside=False, rebin=rebin, xaxis=xaxis, show_ratio=True,ratio_range=0.5)
         #print var, sum(plotter.keep[0].hists).Integral(), plotter.keep[1].Integral()
         plotter.add_cms_blurb(13, lumiformat='%0.3f')
         plotter.save(var, pdf=False)
      
      for info in vars_to_unfold:
         var = info.var
         plotter.plot_mc_vs_data(
            'nosys', '%s' % var, 
            leftside=False, rebin=info.binning.reco, xaxis=info.xtitle,
            show_ratio=True, ratio_range=0.5)
         plotter.add_cms_blurb(13, lumiformat='%0.3f')
         plotter.save(var, pdf=False)
      
         previous = info.binning.reco[0]
         ##plotter.set_subdir('%s/slices' % var)
         ##for idx, vbin in enumerate(info.binning.reco[1:]):
         ##   plotter.plot_mc_vs_data(
         ##      'nosys', '%s_%s' % (discriminant, var), leftside=False, 
         ##      rebin = full_discr_binning[0],
         ##      xaxis=discriminant,
         ##      preprocess=lambda x: urviews.ProjectionView(x, 'X', [previous, vbin])
         ##      )
         ##   plotter.save('%s_slice_%i' % (discriminant, idx), pdf=False)
         ##   
         ##   plotter.plot_mc_shapes(
         ##      'nosys', '%s_%s' % (discriminant, var), leftside=False, 
         ##      rebin = full_discr_binning[0],
         ##      xaxis=discriminant, normalize=True, show_err=True, xrange=(-8,1),
         ##      preprocess=lambda x: urviews.ProjectionView(x, 'X', [previous, vbin]))
         ##   plotter.save('%s_slice_%i_shape' % (discriminant, idx), pdf=False)
         ##   
         ##   plotter.plot_mc_shapes(
         ##      'nosys', '%s_%s' % (discriminant, var), leftside=False, 
         ##      rebin = full_discr_binning[0],
         ##      xaxis=discriminant, normalize=True, show_err=True, xrange=(-8,1),
         ##      preprocess=lambda x: urviews.ProjectionView(x, 'X', [previous, vbin]),
         ##      use_only=set(['ttJets_rightTlep', 'ttJets_wrongAssign', 'ttJets_other']),
         ##      ratio_range=1)
         ##   plotter.save('%s_bkgslice_%i_shape' % (discriminant, idx), pdf=False)
         ##   previous = vbin



   ##################
   #     CARDS
   ##################
   if not opts.noshapes:
      plotter.merge_leptons()

      for info in vars_to_unfold:
         var = info.var
         rootpy.log["/"].info('Making cards for %s' % var)
         plotter.set_subdir(
            os.path.join(
               var,
               opts.subdir,
               info.dir_postfix if hasattr(info, 'dir_postfix') else ''
               )
            )
         for category_name, njets in jet_categories:
            plotter.write_shapes(
               'nosys', var, discriminant, njets, var_binning=info.binning.reco, 
               disc_binning = lambda x, *args: full_discr_binning[0], 
               category_template='Bin%i_'+category_name,
               special_cases = {'qcd' : plotter.make_single_shape, 
                                'vjets' : plotter.make_single_shape}
               ) 
         plotter.add_systematics()
         #plotter.card.add_systematic('lumi', 'lnN', '.*', '[^t]+.*', 1.05)
         plotter.save_card(var)

   if not opts.nomatrices:
      print "\n\n MIGRATION MATRICES  \n\n"
      ########################################
      #         MIGRATION MATRICES
      ########################################
      plotter.set_subdir('')
      fname = os.path.join(plotter.outputdir, 'migration_matrices.root')

      with io.root_open(fname, 'recreate') as mfile:
         response_dir = 'nosys/response'
         for info in vars_to_unfold:
            var = info.var
            dirname = var
            if hasattr(info, 'dir_postfix'):
               dirname += '_%s' % info.dir_postfix
            mfile.mkdir(dirname).cd()
            matrix_path = '%s/%s_matrix' % (response_dir, var)
            tt_view = views.SubdirectoryView(
               plotter.get_view(plotter.ttbar_to_use, 'unweighted_view'),
               'semilep_visible_right'
               )
            tt_view = views.SumView(
               views.SubdirectoryView(tt_view, 'muons'),
               views.SubdirectoryView(tt_view, 'electrons')
               )
               
            matrix_view_unscaled = plotter.rebin_view(
               tt_view, 
               [info.binning.gen, info.binning.reco]
               )
            mig_matrix_unscaled = matrix_view_unscaled.Get(matrix_path)
            mig_matrix_unscaled.SetName('migration_matrix')
            mig_matrix_unscaled.Write()

            thruth_unscaled = plotter.rebin_view(tt_view, info.binning.gen).Get('%s/%s_truth' % (response_dir, var))            
            thruth_unscaled.name = 'thruth_unscaled'
            thruth_unscaled.Write()
            
            reco_unscaled = plotter.rebin_view(tt_view, info.binning.reco).Get('%s/%s_reco' % (response_dir, var))
            reco_unscaled.name = 'reco_unscaled'
            reco_unscaled.Write()

            tt_view = plotter.get_view('ttJets_rightAssign')
            matrix_view = plotter.rebin_view(
               tt_view,
               [info.binning.gen, info.binning.reco]
               )
            mig_matrix = matrix_view.Get(matrix_path)
            mig_matrix.SetName('migration_matrix_scaled')
            mig_matrix.Write()

            reco_distro = mig_matrix.ProjectionY() 
            reco_distro.SetName('reco_distribution')
            reco_distro.Write()
            
            prefit_view = plotter.rebin_view(
               plotter.get_view('ttJets_rightAssign'), 
               info.binning.reco
               )
            plotting.views.SumView.debug = True
            prefit_plot = prefit_view.Get('nosys/%s' % var)
            prefit_plot.name = 'prefit_distribution'
            prefit_plot.Write()

            thruth_distro = plotter.rebin_view(
               tt_view,
               info.binning.gen
               ).Get(
               '%s/%s_truth' % (response_dir, var) )
            thruth_distro.SetName('true_distribution')
            thruth_distro.Write()         

      logging.info('file: %s written' % fname)
      


if __name__ == '__main__':
   parser = ArgumentParser()
   parser.add_argument('--noplots', dest='noplots', action='store_true',
                       help='skip plot making')
   parser.add_argument('--noshapes', dest='noshapes', action='store_true',
                       help='skip shape making')
   parser.add_argument('--optimize_binning', type=str,
                       help='map observable:[] first bin range for optimization'
                       )
   parser.add_argument('--binning', type=str,
                       help='map observable:[binning] binning for optimization'
                       )
   parser.add_argument('--subdir', type=str, default='',
                       help='sub directory to store shapes'
                       )
   parser.add_argument('--lumi', type=float, default=-1.,
                       help='force luminosity'
                       )
   parser.add_argument('--nodata', action='store_true',
                       help='do not use data (best used with --lumi)'
                       )
   parser.add_argument('--nomatrices', action='store_true',
                       help='do not produce matrices'
                       )
   opts = parser.parse_args()
   run_module(**dict(opts._get_kwargs()))
   
