#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
Multivariate Skewed Student (Demarta & McNeil)
==============================================

"""
from __future__ import print_function, division

import numpy as np

from scipy.special import gamma, kv
import scipy.linalg as scl
import scipy.stats as scs

from .multidensity import MultiDensity

__all__ = ['SkStDM']


class SkStDM(MultiDensity):

    """Multidimensional density (Demarta & McNeil).

    Attributes
    ----------
    eta : float
        Degrees of freedom. :math:`4 < \eta < \infty`
    lam : array_like
        Asymmetry. :math:`-\infty < \lambda < \infty`
    data : array_like
        Data grid

    Methods
    -------
    from_theta
        Initialize individual parameters from theta
    rvs
        Simulate random variables

    """

    def __init__(self, ndim=None, eta=10., lam=[.5, 1.5],
                 mu=None, sigma=None, data=None):
        """Initialize the class.

        Parameters
        ----------
        eta : float
            Degrees of freedom. :math:`4 < \eta < \infty`
        lam : array_like
            Asymmetry. :math:`-\infty < \lambda < \infty`
        mu : array_like
            Constant in the mean. None for centered density.
        sigma : array_like
            Covariance matrix. None for standardized density.
        data : array_like
            Data grid

        """
        super(SkStDM, self).__init__(ndim=ndim, eta=eta, lam=lam, data=data)
        self.mu = mu
        self.sigma = sigma

    def get_name(self):
        return 'Demarta & McNeil'

    def from_theta(self, theta=[10., .5, 1.5]):
        """Initialize individual parameters from theta.

        Parameters
        ----------
        theta : array_like
            Density parameters

        """
        self.eta = np.atleast_1d(theta[0])
        self.lam = np.atleast_1d(theta[1:])

    def bounds(self):
        """Parameter bounds.

        Returns
        -------
        list of tuples
            Bounds on each parameter

        """
        bound_eta = [4]
        bound_lam = self.ndim * [None]
        return list(zip(np.concatenate((bound_eta, bound_lam)),
                   (1 + self.ndim) * [None]))

    def theta_start(self, ndim=2):
        """Initialize parameter for optimization.

        Parameters
        ----------
        ndim : int
            Number of dimensions

        Returns
        -------
        array
            Parameters in one vector

        """
        eta = np.array([10])
        lam = np.zeros(ndim)
        return np.concatenate((eta, lam))

    def const_mu(self):
        """Compute a constant.

        Returns
        -------
        (ndim, ) array

        """
        if self.mu is None:
            return self.eta / (2 - self.eta) * self.lam
        else:
            return np.array(self.mu)

    def const_sigma(self):
        """Compute a constant.

        Returns
        -------
        (ndim, ndim) array

        """
        if self.sigma is None:
            ndim = self.lam.size
            return (1 - 2 / self.eta) * np.eye(ndim) \
                - 2 * self.eta  / (self.eta - 2) / (self.eta - 4) \
                * self.lam * self.lam[:, np.newaxis]
        else:
            return np.array(self.sigma)

    def pdf(self, data=None):
        """Probability density function (PDF).

        Parameters
        ----------
        data : array_like
            Grid of point to evaluate PDF at.

            (k,) - one observation, k dimensions

            (T, k) - T observations, k dimensions

        Returns
        -------
        (T, ) array
            PDF values

        """
        ndim = self.lam.size
        if data is None:
            raise ValueError('No data given!')
        self.data = np.atleast_2d(data)
        # (T, k) array
        diff = self.data - self.const_mu()
        # (k, T) array
        diff_norm = scl.solve(self.const_sigma(), diff.T)
        # (T, ) array
        diff_sandwich = (diff.T * diff_norm).sum(0)
        # float
        norm_lam = (self.lam * scl.solve(self.const_sigma(), self.lam)).sum()
        # (T, ) array
        kappa = ((self.eta + diff_sandwich) * norm_lam) ** .5
        return 2 ** (1 - (self.eta + ndim) / 2) \
            / ((np.pi * self.eta) ** ndim * scl.det(self.const_sigma())) **.5 \
            * kv((self.eta + ndim) / 2, kappa) \
            * kappa ** ((self.eta + ndim) / 2) \
            / gamma(self.eta / 2) \
            * np.exp(diff_norm.T.dot(self.lam)) \
            * (1 + diff_sandwich / self.eta) ** (- (self.eta + ndim) / 2)

    def rvs(self, size=10):
        """Simulate random variables.

        Parameters
        ----------
        size : int
            Number of data points

        Returns
        -------
        (size, ndim) array

        """
        igrv = scs.invgamma.rvs(self.eta / 2, scale=self.eta / 2, size=size)
        igrv = igrv[:, np.newaxis]
        mvnorm = scs.multivariate_normal.rvs(cov=self.const_sigma(), size=size)
        return self.const_mu() + self.lam * igrv + igrv ** .5 * mvnorm
