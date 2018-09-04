import logging
import time
import os

__all__ = ["Speedometer",
           "CheckpointManager"]


class Speedometer(object):
    """Logs training speed and evaluation metrics periodically.

    Parameters
    ----------
    batch_size: int
        Batch size of data.
    frequent: int
        Specifies how frequently training speed and evaluation metrics
        must be logged. Default behavior is to log once every 50 batches.
    auto_reset : bool
        Reset the evaluation metrics after each log.

    Example
    -------
    Epoch[0] Batch [10] Speed: 1910.41 samples/sec  Train-accuracy=0.200000
    Epoch[0] Batch [20] Speed: 1764.83 samples/sec  Train-accuracy=0.400000
    Epoch[0] Batch [30] Speed: 1740.59 samples/sec  Train-accuracy=0.500000
    """
    def __init__(self, batch_size, frequent=50, logger=logging.getLogger(), auto_reset=True):
        self.batch_size = batch_size
        self.frequent = frequent
        self.init = False
        self.tic = 0
        self.last_count = 0
        self.auto_reset = auto_reset
        self.logger = logger

    def __call__(self, param):
        """Callback to Show speed."""
        count = param.nbatch
        if self.last_count > count:
            self.init = False
        self.last_count = count

        if self.init:
            if count % self.frequent == 0:
                speed = self.frequent * self.batch_size / (time.time() - self.tic)
                if param.eval_metric is not None:
                    name_value = param.eval_metric.get_name_value()
                    if self.auto_reset:
                        param.eval_metric.reset()
                    msg = 'Epoch[%d] Batch [%d]\tSpeed: %.2f samples/sec'
                    msg += '\t%s=%f'*len(name_value)
                    self.logger.info(msg, param.epoch, count, speed, *sum(name_value, ()))
                else:
                    self.logger.info("Iter[%d] Batch [%d]\tSpeed: %.2f samples/sec",
                                     param.epoch, count, speed)
                self.tic = time.time()
        else:
            self.init = True
            self.tic = time.time()


class CheckpointManager(object):
    def __init__(self, path, prefix="model", num_checkpoint=5, period=1, logger=logging.getLogger()):
        self._period = period
        self._path = path
        self._prefix = prefix
        self._logger = logger
        self._num_checkpoint = num_checkpoint

    def __call__(self, iter_no, net):
        if (iter_no + 1) % self._period != 0:
            return

        net.export(os.path.join(self._path, self._prefix), iter_no)
        self._logger.info("Model at epoch[%d] saved to %s", iter_no, self._path)
        self._clean_files()

    def _clean_files(self):
        file_count = []
        for filename in os.listdir(self._path):
            name, ext = os.path.splitext(filename)
            if ext != ".params":
                continue
            file_count.append(int(name.split("-")[1]))

        if len(file_count) > self._num_checkpoint:
            file_count.sort()
            for i in range(len(file_count) - self._num_checkpoint):
                filename = "-".join([self._prefix, "%04d.params" % file_count[i]])
                os.remove(os.path.join(self._path, filename))
