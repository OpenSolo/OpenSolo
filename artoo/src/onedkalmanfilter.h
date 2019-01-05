#ifndef _ONE_D_KALMAN_FILTER_H
#define _ONE_D_KALMAN_FILTER_H

/*
 * http://interactive-matter.eu/blog/2009/12/18/filtering-sensor-data-with-a-kalman-filter/
 * XXX: would prefer fixed point implementation, this was just quickest.
 * XXX2: simpler low pass may be acceptable for the places this is used at the moment.
 */

template <typename T = float>
class OneDKalmanFilter
{
public:
    OneDKalmanFilter(T q_, T r_, T p_) :
        q(q_),
        r(r_),
        p(p_),
        x(0)
    {}

    void init(T measurement) {
        x = measurement;
    }

    void update(T measurement) {
        // prediction update
        p = p + q;

        T k; // kalman gain
        // measurement update
        k = p / (p + r);
        x = x + k * (measurement - x);
        p = (1 - k) * p;
    }

    inline T val() const {
        return x;
    }

private:
    const T q;  // process noise covariance (assumed noise in real signal)
    const T r;  // measurement noise covariance (assumed noise of sensor)
    T p;        // estimation error covariance (updated throughout filtering)
    T x;        // value
};

#endif // _ONE_D_KALMAN_FILTER_H
