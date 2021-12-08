odoo.define("pms_sale.pms_gantt", function (require) {
    "use strict";

    const core = require("web.core");
    const time = require("web.time");
    const TimelineRenderer = require("web_timeline.TimelineRenderer");
    const _t = core._t;

    TimelineRenderer.include({
        init: function (parent, state, params) {
            var self = this;
            this._super.apply(this, arguments);
            this.modelName = params.model;
            this.date_start = params.date_start;
            this.date_stop = params.date_stop;
            this.view = params.view;

            // Find their matches
            if (this.modelName == "pms.reservation") {
                // Find custom color if mentioned
                if (params.arch.attrs.custom_color === "true") {
                    this._rpc({
                        model: "pms.stage",
                        method: "get_color_information",
                        args: [[]],
                    }).then(function (result) {
                        self.colors = result;
                    });
                }
            }
        },
        on_data_loaded_2: function (events, group_bys, adjust_window) {
            var self = this;
            if (this.modelName == "pms.reservation") {
                var data = [];
                var groups = [];
                this.grouped_by = group_bys;
                _.each(events, function (event) {
                    if (event[self.date_start]) {
                        data.push(self.event_data_transform(event));
                    }
                });
            }
            return this._super.apply(this, arguments);
        },
        event_data_transform: function (evt) {
            if (this.modelName == "pms.reservation") {
                var self = this;
                var date_start = new moment();
                var date_stop = null;
                date_start = time.auto_str_to_date(evt[this.date_start]);
                date_stop = this.date_stop
                    ? time.auto_str_to_date(evt[this.date_stop])
                    : null;
                var group = evt[self.last_group_bys[0]];
                if (group && group instanceof Array) {
                    group = _.first(group);
                } else {
                    group = -1;
                }
                _.each(self.colors, function (color) {
                    if (
                        eval(
                            "'" +
                                evt[color.field] +
                                "' " +
                                color.opt +
                                " '" +
                                color.value +
                                "'"
                        )
                    ) {
                        self.color = color.color;
                    } else if (
                        eval(
                            "'" +
                                evt[color.field][1] +
                                "' " +
                                color.opt +
                                " '" +
                                color.value +
                                "'"
                        )
                    ) {
                        self.color = color.color;
                    }
                });
                var content = _.isUndefined(evt.__name) ? evt.display_name : evt.__name;
                if (this.arch.children.length) {
                    content = this.render_timeline_item(evt);
                }
                var r = {
                    start: date_start,
                    content: content,
                    id: evt.id,
                    group: group,
                    evt: evt,
                    style: "background-color: " + self.color + ";",
                };

                if (date_stop && !moment(date_start).isSame(date_stop)) {
                    r.end = date_stop;
                }
                self.color = null;
                return r;
            }
            return this._super.apply(this, arguments);
        },
    });
});
