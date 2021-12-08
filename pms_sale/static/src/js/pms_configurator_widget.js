odoo.define("pms_sale.product_configurator", function (require) {
    "use strict";

    var ProductConfiguratorWidget = require("sale.product_configurator");

    /**
     * Extension of the ProductConfiguratorWidget to support event product configuration.
     * It opens when an event product_product is set.
     *
     * The event information include:
     * - property_id
     * - reservation_id
     *
     */
    ProductConfiguratorWidget.include({
        /**
         * @returns {Boolean}
         *
         * @override
         * @private
         */
        _isConfigurableLine: function () {
            return this.recordData.reservation_ok || this._super.apply(this, arguments);
        },

        /**
         * @param {integer} productId
         * @param {String} dataPointID
         * @returns {Promise<Boolean>} stopPropagation true if a suitable configurator has been found.
         *
         * @override
         * @private
         */
        _onProductChange: function (productId, dataPointId) {
            var self = this;
            return this._super.apply(this, arguments).then(function (stopPropagation) {
                if (stopPropagation || productId === undefined) {
                    return Promise.resolve(true);
                }
                return self._checkForReservation(productId, dataPointId);
            });
        },

        /**
         * This method will check if the productId needs configuration or not:
         *
         * @param {integer} productId
         * @param {String} dataPointID
         * @returns {Promise<Boolean>} stopPropagation true if the product is an event ticket.
         *
         * @private
         */
        _checkForReservation: function (productId, dataPointId) {
            var self = this;
            return this._rpc({
                model: "product.product",
                method: "read",
                args: [productId, ["reservation_ok"]],
            }).then(function (result) {
                if (
                    Array.isArray(result) &&
                    result.length &&
                    result[0].reservation_ok
                ) {
                    self._openReservationConfigurator(
                        {
                            default_product_id: productId,
                        },
                        dataPointId
                    );
                    return Promise.resolve(true);
                }
                return Promise.resolve(false);
            });
        },

        /**
         * Opens the event configurator in 'edit' mode.
         *
         * @override
         * @private
         */
        _onEditLineConfiguration: function () {
            if (this.recordData.reservation_ok) {
                var defaultValues = {
                    default_product_id: this.recordData.product_id.data.id,
                };

                if (this.recordData.property_id) {
                    defaultValues.default_property_id = this.recordData.property_id.data.id;
                }

                if (this.recordData.reservation_id) {
                    defaultValues.default_reservation_id = this.recordData.reservation_id.data.id;
                }
                if (this.recordData.start) {
                    defaultValues.start = this.recordData.start;
                }
                if (this.recordData.stop) {
                    defaultValues.stop = this.recordData.stop;
                }

                this._openReservationConfigurator(defaultValues, this.dataPointID);
            } else {
                this._super.apply(this, arguments);
            }
        },

        /**
         * Opens the event configurator to allow configuring the SO line with events information.
         *
         * When the window is closed, configured values are used to trigger a 'field_changed'
         * event to modify the current SO line.
         *
         * If the window is closed without providing the required values 'property_id' and
         * 'reservation_id', the product_id field is cleaned.
         *
         * @param {Object} data various "default_" values
         * @param {String} dataPointId
         *
         * @private
         */
        _openReservationConfigurator: function (data, dataPointId) {
            var self = this;

            this.do_action("pms_sale.pms_configurator_action", {
                additional_context: data,
                on_close: function (result) {
                    if (result && !result.special) {
                        self.trigger_up("field_changed", {
                            dataPointID: dataPointId,
                            changes: result.ReservationConfiguration,
                            onSuccess: function () {
                                // Call post-init function.
                                self._onLineConfigured();
                            },
                        });
                    } else if (
                        !self.recordData.property_id ||
                        !self.recordData.reservation_id
                    ) {
                        self.trigger_up("field_changed", {
                            dataPointID: dataPointId,
                            changes: {
                                product_id: false,
                                name: "",
                            },
                        });
                    }
                },
            });
        },
    });

    return ProductConfiguratorWidget;
});
