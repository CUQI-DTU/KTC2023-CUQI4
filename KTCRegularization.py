#%%
import numpy as np

class SMPrior:
    def __init__(self, ginv, corrlength, var, mean, covariancetype=None):
        self.corrlength = corrlength
        self.mean = mean
        self.c = 1e-9  # default value
        if covariancetype is not None:
            self.covariancetype = covariancetype
        else:
            self.covariancetype = 'Squared Distance'  # default
        self.compute_L(ginv, corrlength, var)

    def compute_L(self, g, corrlength, var):
        ng = g.shape[0]
        a = var - self.c
        b = np.sqrt(-corrlength**2 / (2 * np.log(0.01)))
        Gamma_pr = np.zeros((ng, ng))

        for ii in range(ng):
            for jj in range(ii, ng):
                dist_ij = np.linalg.norm(g[ii, :] - g[jj, :])
                if self.covariancetype == 'Squared Distance':
                    gamma_ij = a * np.exp(-dist_ij**2 / (2 * b**2))
                elif self.covariancetype == 'Ornstein-Uhlenbeck':
                    gamma_ij = a * np.exp(-dist_ij / corrlength)
                else:
                    raise ValueError('Unrecognized prior covariance type')
                if ii == jj:
                    gamma_ij = gamma_ij + self.c
                Gamma_pr[ii, jj] = gamma_ij
                Gamma_pr[jj, ii] = gamma_ij
        

        self.L = np.linalg.cholesky(np.linalg.inv(Gamma_pr)).T

    def draw_samples(self, nsamples):
        samples = self.mean + np.linalg.solve(self.L, np.random.randn(self.L.shape[0], nsamples))
        return samples

    def eval_fun(self, args):
        sigma = args[0]
        res = 0.5 * np.linalg.norm(self.L @ (sigma - self.mean))**2
        return res

    def compute_hess_and_grad(self, args, nparam):
        sigma = args[0]
        Hess = self.L.T @ self.L
        grad = Hess @ (sigma - self.mean)

        if nparam > len(sigma):
            Hess = np.block([[Hess, np.zeros((len(sigma), nparam - len(sigma)))],
                             [np.zeros((nparam - len(sigma), len(sigma))), np.zeros((nparam - len(sigma), nparam - len(sigma)))]])
            grad = np.concatenate([grad, np.zeros(nparam - len(sigma))])

        return Hess, grad


if __name__ ==  '__main__':
    from EITLib import EITFenics
    from dolfin import *
    import pickle
    L = 32
    F = 40
    n = 300
    myeit = EITFenics(L=L, n=n, F=F, background_conductivity=0.8)
    H = FunctionSpace(myeit.mesh, 'CG', 1)

    plot(myeit.mesh)

    v2d = vertex_to_dof_map(H)
    d2v = dof_to_vertex_map(H)

    sigma0 = np.ones((myeit.mesh.num_vertices(), 1)) #linearization point
    corrlength =  1#* 0.115 #used in the prior
    var_sigma = 0.05 ** 2 #prior variance
    mean_sigma = sigma0
    smprior = SMPrior(myeit.mesh.coordinates()[d2v], corrlength, var_sigma, mean_sigma)
    

    sample = smprior.draw_samples(1)
    fun = Function(H)
    fun.vector().set_local(sample)
    plot(fun)

    mesh_file =XDMFFile('mesh_file_'+L+'_'+n+'.xdmf')
    mesh_file.write(myeit.mesh)
    mesh_file.close()

    file = open('smprior_50_300.p', 'wb')
    pickle.dump(smprior, file)








# %%
