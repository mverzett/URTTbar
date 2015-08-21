#ifndef IDELECTRON_H
#define IDELECTRON_H
#include "URStreamer.h"
#include "MCMatchable.h"
#include <atomic>

class IDElectron : public Electron, public MCMatchable
{
private:
	double rho_;

public:
	IDElectron(const Electron el, double rho=-1.) : 
		Electron(el),
		MCMatchable(),
		rho_(rho)
	{
	}
	//FIXME
	//why this here? it is likely to break 
  //if we ever move to threaded running!
	static bool USEISO;
	enum IDS {MEDIUM_12, LOOSE_12, MEDIUM_12Db, LOOSE_12Db, MEDIUM_15, LOOSE_15};
	double CorPFIsolation2012(double eta) const;
	double CorPFIsolation2015() const;
	double PFIsoDb() const;
	bool ID(IDS idtyp);

};

#endif
