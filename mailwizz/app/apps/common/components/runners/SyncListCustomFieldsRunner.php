<?php declare(strict_types=1);
if (!defined('MW_PATH')) {
    exit('No direct script access allowed');
}

/**
 * SyncListCustomFieldsRunner
 *
 * @package MailWizz EMA
 * @author MailWizz Development Team <support@mailwizz.com>
 * @link https://www.mailwizz.com/
 * @copyright MailWizz EMA (https://www.mailwizz.com)
 * @license https://www.mailwizz.com/license/
 * @since 2.2.2
 */

final class SyncListCustomFieldsRunner
{
    /**
     * @var int
     */
    private $_listId = 0;

    /**
     * @var null|callable
     */
    private $_logger;

    /**
     * @return int
     */
    public function getListId(): int
    {
        return $this->_listId;
    }

    /**
     * @param int $listId
     *
     * @return $this
     */
    public function setListId(int $listId): self
    {
        $this->_listId = $listId;

        return $this;
    }

    /**
     * @return callable|null
     */
    public function getLogger(): ?callable
    {
        return $this->_logger;
    }

    /**
     * @param callable|null $logger
     *
     * @return $this
     */
    public function setLogger(?callable $logger): self
    {
        $this->_logger = $logger;

        return $this;
    }

    /**
     * @return bool
     * @throws Exception
     */
    public function run(): bool
    {
        // check if pcntl enabled
        $pcntl = CommonHelper::functionExists('pcntl_fork') && CommonHelper::functionExists('pcntl_waitpid');

        $this->log('Processing list id: ' . $this->getListId());

        /** @var int $count */
        $count = (int)ListSubscriber::model()->countByAttributes([
            'list_id' => $this->getListId(),
        ]);

        $cacheKey = sha1(
            'system.cron.process_subscribers.sync_custom_fields_values.list_id.' . $this->getListId() . '.avg_last_updated' .
            '.count_' . $count
        );
        $mutexKey = $cacheKey . ':' . date('Ymd');

        $this->log('Acquiring the mutex lock...');
        if (!mutex()->acquire($mutexKey, 10)) {
            $this->log('Unable to acquire the mutex lock...');
            return false;
        }

        $cachedAvg = (string)cache()->get($cacheKey);
        $row       = db()->createCommand('
			SELECT AVG(last_updated) AS avg_last_updated FROM {{list_field}} WHERE list_id = :lid
		')->queryRow(true, [
            ':lid' => $this->getListId(),
        ]);
        $avgLastUpdated  = (string)$row['avg_last_updated'];
        $invalidateCache = $avgLastUpdated !== $cachedAvg;

        // nothing has changed in the fields, we can stop
        if (!$invalidateCache) {
            $this->log('No change detected in the custom fields for this list!');

            // release the mutex
            mutex()->release($mutexKey);

            return true;
        }

        // load all custom fields for the given list
        $this->log('Loading all custom fields for this list...');
        $sql    = 'SELECT field_id, default_value FROM {{list_field}} WHERE list_id = :lid';
        $fields = db()->createCommand($sql)->queryAll(true, [':lid' => $this->getListId()]);

        $sql    = 'SELECT * FROM {{list_subscriber}} WHERE list_id = :lid ORDER BY subscriber_id ASC LIMIT %d OFFSET %d';
        $limit  = 1000;
        $offset = 0;

        $processesCount = 10;
        while (true) {
            $children = [];
            $batchCounter = [];

            for ($i = 0; $i < $processesCount; $i++) {
                $this->log(sprintf('[%d] Loading subscribers set for the list with limit: %d and offset %d', $i, $limit, $offset));

                $subscribers = db()
                    ->createCommand(sprintf($sql, $limit, $offset))
                    ->queryAll(true, [':lid' => (int)$this->getListId()]);

                $batchCounter[$i] = count($subscribers);
                $offset           = $limit + $offset;

                if (empty($subscribers)) {
                    continue;
                }

                if (!$pcntl) {
                    $this->processBatch($fields, $subscribers, $i);
                } else {

                    // close the external connections
                    CommonHelper::setExternalConnectionsActive(false);

                    $pid = pcntl_fork();
                    if ($pid == -1) {
                        continue;
                    }

                    // Parent
                    if ($pid) {
                        $children[] = $pid;
                    }

                    // Child
                    if (!$pid) {
                        $this->processBatch($fields, $subscribers, $i);
                        app()->end();
                    }
                }
            }

            if ($pcntl) {
                while (count($children) > 0) {
                    foreach ($children as $key => $pid) {
                        $res = pcntl_waitpid($pid, $status, WNOHANG);
                        if ($res == -1 || $res > 0) {
                            unset($children[$key]);
                        }
                    }
                    usleep(500000);
                }
            }

            // if any of the workers has nothing to process it means we're done
            if (count(array_filter(array_values($batchCounter))) != $processesCount) {
                break;
            }
        }

        // update the cache
        cache()->set($cacheKey, $avgLastUpdated);

        // release the mutex
        mutex()->release($mutexKey);

        // and ... done
        $this->log('Done, no more subscribers for this list!');

        return true;
    }

    /**
     * @param array $fields
     * @param array $subscribers
     * @param int $workerNum
     *
     * @throws CDbException
     * @throws CException
     * @throws \MaxMind\Db\Reader\InvalidDatabaseException
     */
    private function processBatch(array $fields = [], array $subscribers = [], int $workerNum = 0): void
    {
        if (empty($fields) || empty($subscribers)) {
            return;
        }

        $this->log(sprintf('[%d] Starting a new batch counting %d subscribers...', $workerNum, count($subscribers)));

        // keep a reference
        $subscribersList = [];
        $sids            = [];
        foreach ($subscribers as $sub) {
            $sids[]                                 = $sub['subscriber_id'];
            $subscribersList[$sub['subscriber_id']] = $sub;
        }

        // since 1.9.10 - we must delete rows with empty values but with default values
        $sql = 'SELECT v.value_id, v.`value`, f.default_value FROM {{list_field_value}} v INNER JOIN {{list_field}} f ON f.field_id = v.field_id WHERE v.subscriber_id IN(' . implode(',', $sids) . ')';
        $fieldsValues = db()->createCommand($sql)->queryAll();
        foreach ($fieldsValues as $fieldValue) {
            if (strlen(trim((string)$fieldValue['value'])) === 0 && strlen(trim((string)$fieldValue['default_value'])) !== 0) {
                db()->createCommand('DELETE FROM {{list_field_value}} WHERE value_id = :id')->execute([
                    ':id' => (int)$fieldValue['value_id'],
                ]);
            }
        }
        //

        // load all custom fields values for existing subscribers
        $sql = 'SELECT field_id, subscriber_id FROM {{list_field_value}} WHERE subscriber_id IN(' . implode(',', $sids) . ')';
        $fieldsValues = db()->createCommand($sql)->queryAll();

        // populate this to have the defaults set so we can diff them later
        $fieldSubscribers = [];
        foreach ($fields as $field) {
            $fieldSubscribers[$field['field_id']] = [];
        }

        // we have set the defaults abive, we now just have to add to the array
        foreach ($fieldsValues as $fieldValue) {
            $fieldSubscribers[$fieldValue['field_id']][] = $fieldValue['subscriber_id'];
        }
        $fieldsValues = null;

        foreach ($fieldSubscribers as $fieldId => $_subscribers) {
            // exclude $subscribers from $sids
            $subscribers = array_diff($sids, $_subscribers);

            if (!count($subscribers)) {
                continue;
            }

            $this->log('[' . $workerNum . '] Field id ' . $fieldId . ' will add ' . count($subscribers) . ' records.');

            $fieldValues = [];
            foreach ($fields as $field) {
                if ($field['field_id'] == $fieldId) {
                    foreach ($subscribers as $subscriber) {
                        $subscriberObject = null;
                        if (isset($subscribersList[$subscriber])) {
                            $subscriberObject = new ListSubscriber();
                            $subscriberObject->setIsNewRecord(false);
                            $subscriberObject->setAttributes($subscribersList[$subscriber], false);
                        }
                        $fieldValues[$subscriber] = ListField::parseDefaultValueTags((string)$field['default_value'], $subscriberObject);
                    }
                    break;
                }
            }

            $inserts = [];
            foreach ($subscribers as $subscriberId) {
                $fieldValue = $fieldValues[$subscriberId] ?? '';
                $inserts[]  = [
                    'field_id'      => $fieldId,
                    'subscriber_id' => $subscriberId,
                    'value'         => $fieldValue,
                    'date_added'    => MW_DATETIME_NOW,
                    'last_updated'  => MW_DATETIME_NOW,
                ];
            }

            $inserts = array_chunk($inserts, 100);
            foreach ($inserts as $insert) {
                $connection = db()->getSchema()->getCommandBuilder();
                $command = $connection->createMultipleInsertCommand('{{list_field_value}}', $insert);
                $command->execute();
            }
            $inserts = null;
        }

        $this->log('[' . $workerNum . '] Batch is done...');
    }

    /**
     * @param string $message
     *
     * @return void
     */
    private function log(string $message): void
    {
        if ($this->getLogger() === null) {
            return;
        }

        call_user_func_array($this->getLogger(), [$message]);
    }
}
