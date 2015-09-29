import React from 'react';
import ReactTooltip from 'react-tooltip';

export default class AutoTagHeaderRowTagCell extends React.Component {

  constructor() {
    super();

    // Prebind this to callback methods
    this.handleCheckedChangeAll = this.handleCheckedChangeAll.bind(this);
  }


  isChecked() {

    for (let image of this.props.images) {
      if (!image.checkedTags.has(this.props.tag)) {
        return false;
      }
    }
    return true;

  }

  handleCheckedChangeAll() {
    this.props.handleCheckedChangeAll(this.props.tag, !this.isChecked());
  }

  render() {
    let token = this.props.token;
    let tag = this.props.tag;

    let tooltipID = 'tooltip-tag-' + tag.id;

    return (
      <th className={"unmatchedTag"}>
        <div className={'token'}>
          <input type="checkbox"
                 checked={this.isChecked()}
                 onChange={this.handleCheckedChangeAll} />
        </div>
        <div className={'tag'}>
          <span style={{position: 'relative'}}>

            <a className={"tag_inner tag_unmatched"}
               data-tip
               data-for={tooltipID}>{tag.value}
            </a>
            <ReactTooltip id={tooltipID} place="bottom" type="dark" effect="solid">
              <ul>
                <li><strong>ID:</strong> {tag.id}</li>
                <li><strong>Value:</strong> {tag.value}</li>
                {
                  tag.description &&
                  <li><strong>Description:</strong> {tag.description}</li>
                }
                <li><strong>Owner:</strong> {tag.owner.omeName}</li>
              </ul>
            </ReactTooltip>

          </span>
        </div>
      </th>
    );
  }
}
